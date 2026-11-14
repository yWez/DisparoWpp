#!/usr/bin/env python3
"""LP Crypto X1 funnel: website registrations, verified joins and broadcast attribution.

The publicly committed file contains aggregate statistics only. All contact IDs,
phones, event IDs and raw source records remain in private Google Sheets / memory.
Never infer WhatsApp group membership from a landing-page registration.
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import logging
import os
import pathlib
import re
from zoneinfo import ZoneInfo
from urllib.parse import quote

import requests
from sync_umclique import sheets_session

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE_ID = os.environ.get("X1_CAPTACAO_SHEET_ID", "1AtxjojmOi3aAFk1gSc1O7Su4pQUSrgsndnNGZkkMU7U")
SOURCE_TAB = "Captação"
GROUP_SHEET_ID = os.environ.get("X1_GROUP_SHEET_ID", "1CPgLkw8jXIT_L9dATUU4gqsjl1vN3V0ANa7zfYQzs3k")
GROUP_TAB = "Entradas Grupo X1"
GROUP_HEADERS = ["data_entrada_confirmada","whatsapp","grupo_id","evidencia","status","campanha_id"]
GROUP_EVIDENCE = {"lista_participantes", "evento_entrada", "webhook_participante", "verificacao_manual", "exportacao_grupo"}
# Approved private worksheets. These are roster snapshots, NOT membership-join events.
# Raw numbers live in private Sheets; never save them to GitHub or logs.
ROSTER_TABS = (
    ("Membros X1 - Mesa 22", "Mesa da Luisa 22/11"),
    ("Membros X1 - Mesa 17-19-22", "Mesa da Luisa 17/19/22"),
)
ROSTER_APPROVED = "LISTA_VERIFICADA"
ROSTER_EVIDENCE = {"lista_participantes", "exportacao_grupo", "verificacao_manual"}

OUT = ROOT / "data" / "x1-attribution.json"
CAMPAIGNS = ROOT / "data" / "disparos.json"
LOG = logging.getLogger("x1_sync")
LOCAL_TZ = ZoneInfo("America/Fortaleza")


def normalize_phone(value):
    digits = re.sub(r"\D", "", str(value or ""))
    return digits or None


def local_registration_time(raw):
    """Parse timestamps without using the host's timezone.

    Google Sheet timestamps are local Fortaleza time when timezone-less; offsets
    are always converted to Fortaleza. No timestamp => unconfirmed date.
    """
    value = str(raw or "").strip()
    if not value:
        return None
    try:
        if re.fullmatch(r"\d{2}/\d{2}/\d{4}(?:\s+\d{2}:\d{2}(?::\d{2})?)?", value):
            date, *time = value.split(maxsplit=1)
            d, m, y = [int(x) for x in date.split("/")]
            value = f"{y:04d}-{m:02d}-{d:02d}" + (" " + time[0] if time else "")
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=LOCAL_TZ)
        return parsed.astimezone(LOCAL_TZ)
    except (ValueError, TypeError):
        return None


def fetch_columns(session, sheet_id=SOURCE_ID):
    """Read only timestamps, phone and UTM columns; never names or emails."""
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values:batchGet"
    params = [
        ("ranges", f"'{SOURCE_TAB}'!A2:A"),
        ("ranges", f"'{SOURCE_TAB}'!D2:D"),
        ("ranges", f"'{SOURCE_TAB}'!H2:K"),
    ]
    response = session.get(url, params=params, timeout=(12, 40))
    response.raise_for_status()
    groups = response.json().get("valueRanges", [])
    if len(groups) != 3:
        raise ValueError("As colunas necessárias da Captação não foram retornadas")
    return [group.get("values", []) for group in groups]


def fetch_group_events(session, sheet_id=GROUP_SHEET_ID):
    """Optional, verified private group membership evidence.

    Missing tab/empty evidence => None (unavailable), NEVER a fictitious zero.
    Group joins can be entered manually from an actual member audit, or by a
    future authenticated webhook. Merely clicking an invite link is insufficient.
    """
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{quote(repr(GROUP_TAB) + '!A1:F', safe='')}"
    response = session.get(url, timeout=(12, 40))
    if response.status_code == 400 and "Unable to parse range" in response.text:
        return None
    if response.status_code == 404 and "Unable to parse range" in response.text:
        return None
    response.raise_for_status()
    rows = response.json().get("values", [])
    if not rows:
        return None
    if [str(x).strip() for x in rows[0][:len(GROUP_HEADERS)]] != GROUP_HEADERS:
        raise ValueError("Cabeçalhos incompatíveis na aba privada de entradas confirmadas")
    return rows[1:]



def fetch_member_rosters(session, sheet_id=GROUP_SHEET_ID):
    """Fetch private roster sources in bulk, with no names, emails or raw logs.

    Each approved sheet is structured as:
      B1 group JID, B2 audit time, B3 LISTA_VERIFICADA,
      B4 evidence, B5 display name, A8:A members (one phone per row).
    """
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values:batchGet"
    params = []
    for title, _ in ROSTER_TABS:
        params.append(("ranges", f"'{title}'!B1:B5"))
        params.append(("ranges", f"'{title}'!A8:A3000"))
    response = session.get(url, params=params, timeout=(12, 40))
    if response.status_code in (400, 404) and "Unable to parse range" in response.text:
        LOG.info("Planilhas privadas dos membros X1 não estão disponíveis.")
        return None
    response.raise_for_status()
    ranges = response.json().get("valueRanges", [])
    if len(ranges) != len(params):
        raise ValueError("Respostas incompletas da lista privada de membros")
    rosters = []
    for j, (title, alias) in enumerate(ROSTER_TABS):
        settings = ranges[2*j].get("values", [])
        member_rows = ranges[2*j+1].get("values", [])
        group_id = value_at(settings, 0)
        timestamp = local_registration_time(value_at(settings, 1))
        status = value_at(settings, 2)
        evidence = value_at(settings, 3).casefold()
        # A pasted list without approval is never counted, and cannot invent 0 matches.
        if status != ROSTER_APPROVED or not group_id.endswith("@g.us") or not timestamp or evidence not in ROSTER_EVIDENCE:
            continue
        raw = [normalize_phone(value_at(member_rows, i)) for i in range(len(member_rows))]
        # BR domestic 10/11-digit values are converted only where unambiguous;
        # malformed/empty entries are excluded rather than matched by guess.
        cleaned = set()
        for phone in raw:
            if phone and len(phone) in (10, 11):
                phone = "55" + phone
            if phone and len(phone) in (12, 13) and phone.startswith("55"):
                cleaned.add(phone)
        if not cleaned:
            continue
        rosters.append({"alias": alias, "group_id": group_id,
                        "checked": timestamp.isoformat(), "phones": cleaned,
                        "source": evidence})
    return rosters


def summarize_member_rosters(rosters, registrations):
    """Verified membership at a time; NEVER proof of when someone entered."""
    if not rosters:
        return {"status": "unavailable", "members": None, "rate": None,
                "matchedByCampaign": {}, "details": [], "lastSnapshotAt": None}
    registered = {x["phone"]: x for x in registrations.values() if x["phone"]}
    known = set()
    details = []
    for roster in rosters:
        phones = set(roster["phones"])
        known.update(phones)
        details.append({"group": roster["alias"], "checkedAt": roster["checked"],
                        "membersAudited": len(phones),
                        "x1Present": len(phones.intersection(registered))})
    match = known.intersection(registered)
    by_campaign = collections.Counter(
        registered[phone]["broadcast"] for phone in match if registered[phone]["broadcast"]
    )
    return {"status": "verified", "members": len(match),
            "rate": len(match)/len(registered) if registered else None,
            "matchedByCampaign": dict(by_campaign),
            "details": details,
            "lastSnapshotAt": max(x["checked"] for x in rosters)}


def value_at(rows, index, col=0):
    return str(rows[index][col] or "").strip() if index < len(rows) and col < len(rows[index]) else ""


def campaign_from_utm(content, utm_campaign, campaign_ids):
    """Only exact per-broadcast UTM values may create a campaign attribution.

    Shared values such as x1-base must never count toward a named broadcast.
    Ambiguous/conflicting campaign IDs are also rejected.
    """
    values = {str(content or "").strip().casefold(), str(utm_campaign or "").strip().casefold()}
    values.discard("")
    matches = []
    for cid in campaign_ids:
        lower = cid.casefold()
        short = lower[:8]
        if any(v in (lower, "x1-" + lower, "disparo-" + lower, "x1-" + short) for v in values):
            matches.append(cid)
    return matches[0] if len(matches) == 1 else None


def unique_registrations(columns, campaigns):
    times, phones, utms = columns
    ids = [str(c.get("campaignId") or c.get("id")) for c in campaigns if c.get("campaignId") or c.get("id")]
    n = max(len(times), len(phones), len(utms))
    unique = {}
    excluded = 0
    all_x1_rows = 0
    for i in range(n):
        source = value_at(utms, i, 0).casefold()
        medium = value_at(utms, i, 1).casefold()
        if source != "whatsapp" or medium != "x1":
            excluded += 1
            continue
        all_x1_rows += 1
        content = value_at(utms, i, 3)
        campaign = value_at(utms, i, 2)
        parsed = local_registration_time(value_at(times, i))
        date = parsed.date().isoformat() if parsed else "Não informada"
        phone = normalize_phone(value_at(phones, i))
        # Without phone we cannot assert two rows belong to the same person.
        key = ("phone", phone) if phone else ("unidentified", i)
        item = {
            "day": date, "time": parsed, "content": content or "Não informada",
            "campaign": campaign or "", "broadcast": campaign_from_utm(content, campaign, ids),
            "has_phone": bool(phone), "phone": phone, "row": i
        }
        prev = unique.get(key)
        # Earliest valid event timestamp wins, independent of sheet row order.
        # Unknown timestamp is always ranked after known timestamps.
        sort_time = parsed.timestamp() if parsed else float("inf")
        prev_time = prev["time"].timestamp() if prev and prev["time"] else float("inf")
        if prev is None or sort_time < prev_time or (sort_time == prev_time and i < prev["row"]):
            unique[key] = item
    return unique, {"sourceRowsRead":n, "x1RowsFound":all_x1_rows,
                    "rowsOutsideX1":excluded, "duplicatesRemoved":all_x1_rows-len(unique)}


def verified_joins(events, registrations):
    """Only unique, evidenced group members among the X1 registrations."""
    if events is None:
        return None
    eligible = {r["phone"] for r in registrations.values() if r["has_phone"]}
    earliest = {}
    for row in events:
        row = (row + [""] * len(GROUP_HEADERS))[:len(GROUP_HEADERS)]
        when, phone, group, evidence, status, _ = [str(x).strip() for x in row]
        phone = normalize_phone(phone)
        if (status.casefold() != "confirmado"
            or evidence.casefold() not in GROUP_EVIDENCE
            or not group or not phone or phone not in eligible):
            continue
        date = local_registration_time(when)
        if date is None:
            continue
        stamp = date.timestamp()
        if phone not in earliest or stamp < earliest[phone][0]:
            earliest[phone] = (stamp, date.date().isoformat())
    # Having a configured sheet with only headers is not evidence of any group
    # member: keep unavailable until there is verified input.
    if not earliest:
        return None
    return earliest


def build_summary(columns, campaigns, now, group_events=None, member_rosters=None):
    unique, diag = unique_registrations(columns, campaigns)
    phones = {r["phone"]:r for r in unique.values() if r["phone"]}
    joins = verified_joins(group_events, unique)
    presence = summarize_member_rosters(member_rosters, unique)
    days = collections.Counter(x["day"] for x in unique.values())
    # Never publish arbitrary raw UTM text: users may paste personal data into UTMs.
    contents = collections.Counter(
        "x1-base" if str(x["content"]).casefold()=="x1-base"
        else "UTM de disparo verificada" if x["broadcast"]
        else "UTM não identificável"
        for x in unique.values()
    )
    per_campaign = collections.Counter(x["broadcast"] for x in unique.values() if x["broadcast"])
    joined_campaigns = collections.Counter()
    if joins is not None:
        for phone in joins:
            campaign = phones[phone]["broadcast"]
            if campaign:
                joined_campaigns[campaign] += 1
    join_days = collections.Counter(v[1] for v in joins.values()) if joins is not None else None
    unattr = sum(x["broadcast"] is None for x in unique.values())
    timestamp = now if isinstance(now,str) else now.isoformat()
    return {
        "meta": {
            "schemaVersion": 2,
            "source": "Google Sheets • Captação • LP Crypto Black 2026",
            "filter": {"utm_source": "whatsapp", "utm_medium": "x1"},
            "lastSyncedAt": timestamp,  # successful authenticated source check
            "lastCheckedAt": timestamp,
            "definition": "Cadastros na página LP com deduplicação cronológica; não comprova entrada em grupo",
            "attributionRule": "Somente ID exato de disparo em utm_campaign/utm_content, primeira inscrição por telefone",
            "groupRule": "Entrada apenas com evento/checagem de participantes documentada na aba privada; clique em convite não conta",
            "groupStatus": "verified" if joins is not None else "unavailable",
            "memberStatus": presence["status"],
            "memberSnapshotAt": presence["lastSnapshotAt"],
            "memberRule": "Lista de membros conferida por administrador: presença atual, NÃO momento de entrada",
            "privacy": "Somente contagens agregadas; telefones, nomes e eventos privados nunca publicados"
        },
        "registrations": len(unique),
        "uniquePhones": len(phones),
        "registrationsWithoutPhone": len(unique) - len(phones),
        "sourceRowsRead": diag["sourceRowsRead"],
        "x1RowsFound": diag["x1RowsFound"],
        "duplicatesRemoved": diag["duplicatesRemoved"],
        "groupMembersVerified": presence["members"],
        "groupMemberRate": presence["rate"],
        "memberGroups": presence["details"],
        "groupJoins": len(joins) if joins is not None else None,
        "groupJoinRate": (len(joins)/len(phones)) if joins is not None and phones else None,
        "groupJoinDaily": ([{"day": d, "joins": n} for d,n in sorted(join_days.items())]
                           if join_days is not None else None),
        "daily": [{"day": d, "registrations": n} for d,n in sorted(days.items())],
        "utmContents": [{"value": v, "registrations": n} for v,n in sorted(contents.items())],
        "byCampaign": [{
            "campaignId": cid, "registrations": count, "method": "utm_individual",
            "groupJoins": joined_campaigns[cid] if joins is not None else None,
            "groupMembersVerified": presence["matchedByCampaign"].get(cid, 0) if presence["status"] == "verified" else None
        } for cid,count in sorted(per_campaign.items())],
        "unattributedRegistrations": unattr,
        "attributionCoverage": (len(unique)-unattr)/len(unique) if unique else None
    }


def run():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    credential = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not credential:
        LOG.warning("Credenciais Google ausentes; resumo X1 anterior preservado.")
        return False
    try:
        session = sheets_session(credential)
        cols = fetch_columns(session)
        try:
            group_events = fetch_group_events(session)
        except requests.HTTPError as exc:
            # Do not confuse a permission issue with zero confirmed members.
            LOG.warning("Entrada no grupo indisponível (%s); nenhum número de grupo será inventado.",
                        type(exc).__name__)
            group_events = None
        try:
            member_rosters = fetch_member_rosters(session)
        except (requests.HTTPError, ValueError) as exc:
            LOG.warning("Relação de membros não disponível (%s), presença permanecerá sem número.", type(exc).__name__)
            member_rosters = None
        campaigns = json.loads(CAMPAIGNS.read_text(encoding="utf-8")).get("campaigns", [])
        now = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
        data = build_summary(cols, campaigns, now, group_events, member_rosters)
    except Exception as exc:
        LOG.warning("Não foi possível consultar Captação (%s); resumo anterior preservado.",
                    type(exc).__name__)
        return False
    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    # A successful source check is recorded even when counts do not change.
    # This avoids an old last-update timestamp being mistaken for an API outage.
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LOG.info("X1 verificado: %d cadastros únicos; %d sem UTM por disparo; eventos de entrada %s.",
             data["registrations"], data["unattributedRegistrations"],
             "verificado" if data["groupJoins"] is not None else "indisponível")
    LOG.info("Membros X1 presentes, com evidência: %s.",
             data["groupMembersVerified"] if data["groupMembersVerified"] is not None else "não disponível")
    return data != previous


if __name__ == "__main__":
    run()
