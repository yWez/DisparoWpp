#!/usr/bin/env python3
"""Read-only UmClique broadcast sync -> Google Sheets + public aggregate JSON.

Secrets must be configured in GitHub Actions; never commit API keys or PII.
The public JSON includes only campaign-level aggregates.
"""
import datetime as dt
import json
import logging
import os
import pathlib
import sys
import time
from zoneinfo import ZoneInfo

import requests
from enrichment import sanitize_errors, sanitize_channel_list, assign_origins
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_ROOT = "https://api.umcliquedigital.com/functions/v1"
ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "disparos.json"
TAB = "Disparos WhatsApp"
SHEET_RANGE = "'Disparos WhatsApp'!A4:U1000"
TIMEZONE = ZoneInfo("America/Fortaleza")
LOG = logging.getLogger("umclique_sync")
FIRST_CAMPAIGN_ROW = 5
TOTAL_ROW = 24
LEGACY_END = "2026-11-10"


def required_env(key):
    value = os.getenv(key, "").strip()
    if not value:
        raise RuntimeError(f"Configuração obrigatória ausente: {key}. Configure nos Secrets/Variables do GitHub.")
    return value


def as_count(value):
    if value is None or value == "":
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError("Contador de campanha inválido") from None
    if parsed < 0:
        raise ValueError("Contador negativo em campanha")
    return parsed


def pick_count(*values):
    for value in values:
        if value is not None:
            return as_count(value)
    return None


def safe_iso(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError:
        return None


def local_date(timestamp):
    when = safe_iso(timestamp)
    if not when:
        return None
    return dt.datetime.fromisoformat(when.replace("Z", "+00:00")).astimezone(TIMEZONE)


def status_pt(value):
    return {
        "completed": "Concluída", "sending": "Em envio", "scheduled": "Agendada",
        "draft": "Rascunho", "paused": "Pausada", "cancelled": "Cancelada",
        "stopped": "Interrompida", "failed": "Falhou"
    }.get(value, "Desconhecido")


def get_json(session, path, **params):
    resp = session.get(API_ROOT + path, params=params or None, timeout=(12, 35))
    resp.raise_for_status()
    body = resp.json()
    if not isinstance(body, dict):
        raise ValueError("Resposta UmClique inesperada, objeto JSON esperado.")
    return body


def api_session(api_key):
    session = requests.Session()
    session.headers.update({"X-API-Key": api_key, "Accept": "application/json"})
    retry = Retry(total=3, backoff_factor=1.5, status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["GET"])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def discover_channel_ids(session, created_from):
    """Find authorized Meta channels from the seven historical LP Crypto campaigns.

    Fail closed: ambiguous/missing historical matches must not import arbitrary accounts.
    No channel IDs are printed or published.
    """
    import re
    expected_contacts = {1: 51, 2: 50, 3: 51, 4: 150, 5: 150, 6: 150, 7: 150}
    matched = {}
    offset = 0
    seen_offsets = set()
    for _ in range(100):
        if offset in seen_offsets:
            raise RuntimeError("Paginação repetida ao descobrir canais")
        seen_offsets.add(offset)
        body = get_json(session, "/public-broadcasts",
                        provider="meta", created_from=created_from,
                        sort="created_at", order="asc", limit=100, offset=offset)
        batches = body.get("broadcasts")
        if not isinstance(batches, list):
            raise ValueError("API não retornou lista de transmissões")
        for item in batches:
            if not isinstance(item, dict):
                continue
            match = re.fullmatch(r"Disparo\s*([1-7])\s*-\s*Wes",
                                 str(item.get("name", "")).strip(), re.I)
            if not match or not item.get("id"):
                continue
            number = int(match.group(1))
            if as_count(item.get("total_contacts")) != expected_contacts[number]:
                continue
            created = local_date(item.get("created_at") or item.get("started_at"))
            if not created or created.date().isoformat() not in ("2026-11-09", "2026-11-10"):
                continue
            meta_channels = {str(ch.get("channel_id"))
                             for ch in item.get("channels") or []
                             if ch.get("provider") == "meta" and ch.get("channel_id")}
            if not meta_channels:
                continue
            key = str(item["id"])
            matched.setdefault(number, {})[key] = meta_channels
        nxt = body.get("next_offset")
        if nxt in (None, "", False):
            break
        offset = int(nxt)
    else:
        raise RuntimeError("Número máximo de páginas na descoberta de canais")
    if set(matched) != set(expected_contacts) or any(len(x) != 1 for x in matched.values()):
        raise RuntimeError(
            "Não foi possível identificar unicamente os sete disparos históricos. "
            "Configure UMCLIQUE_CHANNEL_IDS com os canais autorizados."
        )
    channels = sorted(set().union(*(next(iter(group.values())) for group in matched.values())))
    if not 1 <= len(channels) <= 3:
        raise RuntimeError("Quantidade inesperada de canais Meta; revisar configuração")
    LOG.info("Canais Meta reconhecidos pelos sete disparos históricos: %d", len(channels))
    return channels


def list_broadcasts(session, channel_ids, created_from):
    """List ALL broadcasts owned by the authenticated UmClique company.

    Prior implementation silently restricted results to two historic Meta
    channels; LP Crypto uses both Meta and QR/UAzAPI. Optional explicit
    channel IDs are supported for diagnostics only, never for the default
    dashboard production sync.
    """
    if isinstance(channel_ids, str):
        channel_ids = [v.strip() for v in channel_ids.split(",") if v.strip()]
    selected = list(dict.fromkeys(channel_ids or []))
    if len(selected) > 10:
        raise ValueError("Muitos canais informados para consulta específica")
    scopes = selected if selected else [None]
    collected = {}
    for channel_id in scopes:
        offset, seen_offsets = 0, set()
        for _ in range(100):
            if offset in seen_offsets:
                raise RuntimeError("Paginação UmClique retornou offset repetido")
            seen_offsets.add(offset)
            params = {"created_from": created_from, "sort":"created_at",
                      "order":"asc", "limit":100, "offset":offset}
            if channel_id is not None:
                params["channel_id"] = channel_id
            result = get_json(session, "/public-broadcasts", **params)
            batch = result.get("broadcasts")
            if not isinstance(batch,list):
                raise ValueError("Campo broadcasts ausente/inválido na API")
            for item in batch:
                if isinstance(item,dict) and item.get("id"):
                    collected[str(item["id"])] = item
            nxt = result.get("next_offset")
            if nxt in (None,"",False):
                break
            offset = int(nxt)
            if offset < 0:
                raise ValueError("next_offset inválido")
        else:
            raise RuntimeError("Limite de páginas de campanhas excedido")
    return list(collected.values())


def try_metrics(session, campaign_id):
    try:
        return get_json(session, "/public-broadcasts/" + requests.utils.quote(str(campaign_id), safe="") + "/metrics")
    except (requests.RequestException, ValueError) as exc:
        LOG.warning("Métricas não consultadas para %s: %s", str(campaign_id)[:40], type(exc).__name__)
        return {}


def public_record(item, metrics=None):
    """Strict allowlist: never serialize contacts, recipient lists, phones or message bodies."""
    metrics = metrics or {}
    if not isinstance(item, dict) or not item.get("id") or not item.get("name"):
        raise ValueError("Transmissão sem id/nome oficial")
    counter = metrics.get("counters") or {}
    qstatus = metrics.get("queue_by_status") or {}
    bychan = metrics.get("by_channel") or []
    channels = item.get("channels") or []
    channel = channels[0] if len(channels) == 1 else {}
    channel_ids = sorted({str(ch.get("channel_id")) for ch in channels if ch.get("channel_id")})
    providers=sorted({str(ch.get("provider") or "").lower() for ch in channels if ch.get("provider")})
    provider=providers[0] if len(providers)==1 else "multiple" if providers else "unknown"
    provider_name={"meta":"WhatsApp API Oficial","uazapi":"WhatsApp QR Code",
                   "wapi":"WhatsApp QR Code"}.get(provider,"Múltiplos provedores" if provider=="multiple" else "Provedor não informado")


    def channel_sum(key):
        if not bychan or not all(isinstance(x, dict) and x.get(key) is not None for x in bychan):
            return None
        return sum(as_count(x[key]) for x in bychan)

    sent = pick_count(item.get("sent_count"), counter.get("sent_count"), channel_sum("sent"))
    failed = pick_count(item.get("failed_count"), qstatus.get("failed"), channel_sum("failed"))
    contacts = pick_count(item.get("total_contacts"), counter.get("total_contacts"))
    delivered = pick_count(item.get("delivered_count"), channel_sum("delivered"))
    read = pick_count(item.get("read_count"), channel_sum("read"))
    responded = pick_count(item.get("responded_count"))
    conversions = pick_count(item.get("conversion_count"), (metrics.get("conversions") or {}).get("count"))
    conversion_value = (metrics.get("conversions") or {}).get("total_value")
    if sent is not None and failed is not None and failed > sent:
        LOG.warning("Falhas superiores a enviados para %s; verificar semântica do provedor", item["id"])
    when = local_date(item.get("started_at") or item.get("created_at"))
    created_at = safe_iso(item.get("created_at"))
    date_label = when.strftime("%d/%m/%Y %H:%M") if when else "Horário não informado"
    return {
        "id": str(item["id"]), "campaignId": str(item["id"]),
        "name": str(item["name"])[:140], "status": status_pt(item.get("status")),
        "statusCode": str(item.get("status") or ""), "channel": provider_name, "provider": provider,
        "channelId": str(channel.get("channel_id") or "") if len(channel_ids)==1 else "",
        "channelIds": channel_ids,
        "template": str(channel.get("template_name") or ""),
        "contacts": contacts, "sent": sent, "failures": failed,
        "delivered": delivered, "read": read, "replied": responded,
        "conversions": conversions, "conversionValue": conversion_value,
        "createdAt": created_at, "startedAt": safe_iso(item.get("started_at")),
        "completedAt": safe_iso(item.get("completed_at")),
        "period": when.strftime("%d/%m/%Y") if when else "Não informado",
        "timeLabel": date_label, "source": "umclique_api"
    }


def stable_business_fields(item):
    return {k: v for k, v in item.items() if k not in {"lastSyncedAt", "note", "legacyId", "source"}}


def canonical_name(value):
    """Normalize dash spacing/case to reconcile manual and API campaign labels."""
    import re
    return re.sub(r"\s+", " ", re.sub(r"\s*-\s*", " - ", str(value or "").strip())).casefold()


def merge_records(current, incoming, now):
    """Idempotent by official ID. Safe legacy reconciliation, no silent duplicates."""
    records = list(current)
    modified = []
    warnings = []
    for new in incoming:
        cid = new["campaignId"]
        match_index = next((i for i, old in enumerate(records)
                            if old.get("campaignId") == cid or old.get("id") == cid), None)
        if match_index is None:
            # A legacy record should be reconciled only when name is unique and date is in
            # the historic 9-10 November window; duplicate or uncertain matches are quarantined.
            matching_legacy = [
                i for i, old in enumerate(records)
                if not old.get("campaignId") and str(old.get("id", "")).startswith("D")
                and canonical_name(old.get("name")) == canonical_name(new["name"])
            ]
            created = local_date(new.get("createdAt") or new.get("startedAt"))
            historical = bool(created and "2026-11-09" <= created.date().isoformat() <= LEGACY_END)
            if matching_legacy and historical and len(matching_legacy) == 1 and (
                records[matching_legacy[0]].get("contacts") in (None, new.get("contacts"))
            ):
                match_index = matching_legacy[0]
            elif matching_legacy:
                warnings.append("Campanha com nome semelhante ao histórico não conciliada: " + new["name"])
                continue
        if match_index is None:
            record = dict(new)
            record["lastSyncedAt"] = now
            records.append(record)
            modified.append(record)
        else:
            old = records[match_index]
            record = dict(old)
            record.update(new)
            if old.get("id") != cid:
                record["legacyId"] = old["id"]
            if old.get("note"):
                record["note"] = old["note"]
            if stable_business_fields(old) != stable_business_fields(record):
                record["lastSyncedAt"] = now
                records[match_index] = record
                modified.append(record)
    return records, modified, warnings


def sheets_session(credentials_json):
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    info = json.loads(credentials_json)
    if info.get("type") != "service_account":
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON não contém uma service account válida")
    credentials = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return AuthorizedSession(credentials)


def sheets_get(session, sheet_id):
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{requests.utils.quote(SHEET_RANGE, safe='')}"
    response = session.get(url, timeout=(12, 35))
    response.raise_for_status()
    return response.json().get("values", [])


def find_sheet_rows(values):
    ids, names, blanks = {}, {}, []
    # Range starts at row 4 (header), total is at row 24. No contact data.
    for rownum in range(5, 1001):
        row = values[rownum - 4] if rownum - 4 < len(values) else []
        if rownum == TOTAL_ROW:
            continue
        if not any(str(v).strip() for v in row):
            blanks.append(rownum)
            continue
        if len(row) > 12 and row[12]:
            ids[str(row[12])] = rownum
        if len(row) > 1 and row[1]:
            names.setdefault(canonical_name(row[1]), []).append(rownum)
    return ids, names, blanks


def sheet_values(record, rownum, original=None):
    original = (original or []) + [""] * 21
    def read_number(value):
        return "" if value is None else value
    return [
        record.get("period") or original[0], record.get("name") or original[1],
        record.get("timeLabel") or original[2],
        read_number(record.get("contacts")), read_number(record.get("sent")),
        read_number(record.get("failures")), f'=IF(OR(E{rownum}="";F{rownum}="");"";E{rownum}-F{rownum})',
        f'=IF(OR(E{rownum}="";E{rownum}=0;F{rownum}="");"";F{rownum}/E{rownum})', record.get("status") or "",
        "Meta API Oficial", record.get("template") or original[10],
        original[11] or "Fonte UmClique API • métricas por campanha",
        record.get("campaignId") or "", record.get("startedAt") or "",
        record.get("completedAt") or "", read_number(record.get("delivered")),
        read_number(record.get("read")), read_number(record.get("replied")),
        record.get("lastSyncedAt") or "", "UmClique API",
        "Conciliado por ID" if original[12] else "Identificado via API"
    ]


def sync_sheet(session, sheet_id, modified, all_records):
    """Upsert only changed campaigns. Never write to row 24 (TOTAL PERÍODO)."""
    if not modified:
        return 0
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values:batchUpdate"
    values = sheets_get(session, sheet_id)
    ids, names, blanks = find_sheet_rows(values)
    occupied = set()  # track rows claimed in THIS batch, not all preexisting rows
    updates = []
    for record in modified:
        cid = record.get("campaignId")
        if not cid:
            continue
        rownum = ids.get(cid)
        if rownum is None and record.get("legacyId"):
            legacy_rows = names.get(canonical_name(record["name"]), [])
            if len(legacy_rows) == 1:
                rownum = legacy_rows[0]
        if rownum is None:
            # A matching manual record without a validated legacyId MUST be verified
            # instead of adding the same campaign a second time.
            ambiguous = [r for r in names.get(canonical_name(record["name"]), [])
                         if r <= 11]
            if ambiguous:
                raise RuntimeError("Conciliação manual pendente no Sheets para: " + record["name"])
            rownum = next((r for r in blanks if r not in occupied), None)
            if rownum is None:
                raise RuntimeError("Planilha sem linhas livres no intervalo 5–1000")
        if rownum == TOTAL_ROW or rownum in occupied:
            raise RuntimeError(f"Colisão de linha no Google Sheets: {rownum}")
        occupied.add(rownum)
        original = values[rownum - 4] if rownum - 4 < len(values) else []
        updates.append({
            "range": f"'{TAB}'!A{rownum}:U{rownum}",
            "values": [sheet_values(record, rownum, original)]
        })
    if not updates:
        return 0
    response = session.post(url, json={"valueInputOption": "USER_ENTERED", "data": updates},
                            timeout=(12, 50))
    response.raise_for_status()
    result = response.json()
    if result.get("totalUpdatedRows", 0) < len(updates):
        raise RuntimeError("Google Sheets confirmou menos linhas do que as enviadas")
    return len(updates)


def save_public_json(existing, records, changed, now, channels=None, force=False):
    if not changed and not force:
        return False
    meta = dict(existing.get("meta") or {})
    meta.update({
        "periodLabel": "Campanhas desde 09/11/2026",
        "lastSyncedAt": now,
        "snapshotDate": now[:10],
        "dataStatus": "Sincronizado da UmClique API; campos ausentes não significam zero.",
        "source": "UmClique API (estatísticas agregadas) e captura inicial de 09–10/11/2026",
        "schemaVersion": 2,
        "privacy": "Sem dados pessoais; relatórios individuais somente em ambiente restrito"
    })
    dates=sorted({local_date(r.get("startedAt") or r.get("createdAt")).date().isoformat()
                  for r in records
                  if local_date(r.get("startedAt") or r.get("createdAt"))})
    if dates:
        meta["periodStart"]=dates[0]
        meta["periodEnd"]=dates[-1]
        meta["periodLabel"]="Campanhas de "+dates[0]+" até "+dates[-1]
    document = {"meta": meta, "campaigns": records, "channels": channels or []}
    DATA_PATH.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def run():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    api_key = required_env("UMCLIQUE_API_KEY")
    channel_ids = os.getenv("UMCLIQUE_CHANNEL_IDS", "").strip()
    sheet_id = required_env("GOOGLE_SHEET_ID")
    google_creds = required_env("GOOGLE_SERVICE_ACCOUNT_JSON")
    created_from = os.getenv("UMCLIQUE_CREATED_FROM", "2026-11-09T00:00:00-03:00")
    now = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    existing = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    api = api_session(api_key)
    # Do not restrict the commercial dashboard to legacy Meta channels.
    # The company API key is already scoped to this authorized UmClique account.
    if channel_ids:
        LOG.warning("UMCLIQUE_CHANNEL_IDS legado ignorado: consulta ampla da empresa habilitada")
    broadcasts = list_broadcasts(api, [], created_from)
    LOG.info("Transmissões encontradas na API: %d", len(broadcasts))
    all_providers=sorted({str(ch.get("provider") or "unknown")
        for item in broadcasts for ch in (item.get("channels") or [])})
    LOG.info("Provedores reconhecidos nas campanhas: %s", ", ".join(all_providers) or "não informado")
    current_by_id = {str(x.get("campaignId") or x.get("id")): x for x in existing["campaigns"]}
    normalized = []
    for item in broadcasts:
        if not isinstance(item, dict) or not item.get("id"):
            LOG.warning("Registro sem ID ignorado")
            continue
        old = current_by_id.get(str(item["id"]))
        # Query the detailed metrics only for new/changed or active campaigns.
        base_changes = old is None or any(
            old.get(dst) != item.get(src)
            for dst, src in [("sent", "sent_count"), ("failures", "failed_count"),
                             ("delivered", "delivered_count"), ("read", "read_count"),
                             ("replied", "responded_count")]
        )
        metrics = try_metrics(api, item["id"]) if base_changes or item.get("status") == "sending" else {}
        normalized.append(public_record(item, metrics))
    # Enrichment reads only aggregate error diagnostics and public-safe channel names.
    # Never request or publish recipient lists, phone numbers, message bodies or logs.
    allowed_channels = sorted({x for row in normalized for x in row.get("channelIds", [])})
    channel_public = existing.get("channels", [])
    try:
        response = get_json(api, "/public-channels")
        channel_public = sanitize_channel_list(response, allowed_channels)
    except (requests.RequestException, ValueError, TypeError) as exc:
        LOG.warning("Metadados dos canais indisponíveis: %s", type(exc).__name__)

    for new in normalized:
        old = current_by_id.get(str(new["campaignId"])) or {}
        report = None
        if new.get("failures") is not None and new["failures"] > 0:
            try:
                cid = requests.utils.quote(str(new["campaignId"]), safe="")
                report = sanitize_errors(get_json(api, "/public-broadcasts/" + cid + "/errors"))
            except (requests.RequestException, ValueError, TypeError) as exc:
                LOG.warning("Diagnóstico indisponível para %s: %s", str(new["campaignId"])[:24], type(exc).__name__)
        new["errorDiagnostics"] = report if report is not None else old.get("errorDiagnostics")
        if new["errorDiagnostics"] is not None:
            diagnostic = new["errorDiagnostics"]
            grouped_total = sum(g.get("count", 0) for g in diagnostic.get("groups", []))
            diagnostic["groupCount"] = grouped_total
            official_failed = diagnostic.get("summary", {}).get("failedTotal")
            diagnostic["matchesBroadcastFailures"] = (
                official_failed == new.get("failures")
                if official_failed is not None and new.get("failures") is not None
                else None
            )
        if len(new.get("channelIds",[])) > 1:
            new["channelName"] = "Múltiplos canais (não rateado)"
        else:
            selected = next((v for v in channel_public if v["id"]==new.get("channelId")), None)
            new["channelName"] = selected["name"] if selected else old.get("channelName") or "Canal sem identificação"
        new["channelStatus"] = next((v.get("status") for v in channel_public if v["id"]==new.get("channelId")), None) or old.get("channelStatus")
        # Explicit data lineage: cannot derive unique contacts from aggregated campaigns.
        new["uniqueReached"] = None

    records, changed, warnings = merge_records(existing.get("campaigns", []), normalized, now)
    for warning in warnings:
        LOG.warning("%s", warning)
    if warnings:
        raise RuntimeError("Há campanhas com nome do histórico não conciliado. Reveja os IDs; dados não publicados.")
    origins_file = ROOT / "data" / "origins.json"
    origin_map = {}
    if origins_file.exists():
        blob = json.loads(origins_file.read_text(encoding="utf-8"))
        origin_map = blob.get("campaignOrigins") or {}
        if not isinstance(origin_map, dict):
            raise ValueError("O mapa de origens precisa ser um objeto")
    records = assign_origins(records, origin_map)
    # A changed origin mapping affects the public aggregated dashboard even
    # if the UmClique counters have not changed.
    prior_origins = {str(v.get("campaignId") or v.get("id")):v.get("campaignOrigin")
                     for v in existing.get("campaigns", [])}
    origins_changed = any(v.get("campaignOrigin") != prior_origins.get(str(v.get("campaignId") or v.get("id")))
                          for v in records)
    google = sheets_session(google_creds)
    synced = sync_sheet(google, sheet_id, changed, records)
    channels_changed = channel_public != existing.get("channels", [])
    public_changed = save_public_json(existing, records, changed, now, channel_public,
                                      force=channels_changed or origins_changed)
    LOG.info("Sheets atualizado: %d | JSON alterado: %s", synced, public_changed)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        pathlib.Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8").write(
            f"### UmClique → LP Crypto\n- Campanhas consultadas: {len(broadcasts)}\n"
            f"- Campanhas atualizadas: {len(changed)}\n- Linhas no Sheets: {synced}\n"
            f"- JSON alterado: {public_changed}\n"
        )


if __name__ == "__main__":
    try:
        run()
    except Exception as error:
        LOG.error("Sincronização interrompida: %s", error)
        sys.exit(1)
