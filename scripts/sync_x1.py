#!/usr/bin/env python3
"""Public, aggregated X1 registration attribution from LP Crypto's private Captação sheet.

Only UTM totals and counts are committed. No phone numbers, names or emails leave memory.
An LP registration is NOT proof that a person joined a WhatsApp group.
"""
import collections
import datetime as dt
import json
import logging
import os
import pathlib
import re

import requests
from sync_umclique import sheets_session

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE_ID = os.environ.get("X1_CAPTACAO_SHEET_ID", "1AtxjojmOi3aAFk1gSc1O7Su4pQUSrgsndnNGZkkMU7U")
SOURCE_TAB = "Captação"
OUT = ROOT / "data" / "x1-attribution.json"
CAMPAIGNS = ROOT / "data" / "disparos.json"
LOG = logging.getLogger("x1_sync")


def normalize_phone(value):
    digits = re.sub(r"\D", "", str(value or ""))
    return digits or None


def fetch_columns(session, sheet_id=SOURCE_ID):
    """Read minimal required ranges; never request names, email or event IDs."""
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


def value_at(rows, index, col=0):
    return str(rows[index][col] or "").strip() if index < len(rows) and col < len(rows[index]) else ""


def campaign_from_utm(content, utm_campaign, campaign_ids):
    """Only uniquely identifiable per-broadcast UTM values may be attributed."""
    values = [content.strip().casefold(), utm_campaign.strip().casefold()]
    matches = []
    for cid in campaign_ids:
        lower = cid.casefold()
        short = lower[:8]
        if any(v in (lower, "x1-" + lower, "disparo-" + lower, "x1-" + short) for v in values):
            matches.append(cid)
    return matches[0] if len(matches) == 1 else None


def build_summary(columns, campaigns, now):
    times, phones, utms = columns
    ids = [str(c.get("campaignId") or c.get("id")) for c in campaigns if c.get("campaignId") or c.get("id")]
    n = max(len(times), len(phones), len(utms))
    unique = {}
    seen_without_phone = set()
    for i in range(n):
        source = value_at(utms, i, 0).casefold()
        medium = value_at(utms, i, 1).casefold()
        if source != "whatsapp" or medium != "x1":
            continue
        content = value_at(utms, i, 3)
        campaign = value_at(utms, i, 2)
        date = value_at(times, i)[:10]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            date = "Não informada"
        phone = normalize_phone(value_at(phones, i))
        # A row without phone is kept distinct but not counted as a unique phone.
        key = ("phone", phone) if phone else ("unidentified", i)
        if key in unique:
            continue
        unique[key] = {"day": date, "content": content or "Não informada", "campaign": campaign or "",
                       "broadcast": campaign_from_utm(content, campaign, ids), "has_phone": bool(phone)}
    days = collections.Counter(x["day"] for x in unique.values())
    contents = collections.Counter(x["content"] for x in unique.values())
    per_campaign = collections.Counter(x["broadcast"] for x in unique.values() if x["broadcast"])
    return {
        "meta": {
            "source": "Google Sheets • Captação • LP Crypto Black 2026",
            "filter": {"utm_source": "whatsapp", "utm_medium": "x1"},
            "lastSyncedAt": now,
            "definition": "Cadastros confirmados na página LP; não significa entrada confirmada no grupo",
            "status": "Atribuição por disparo apenas com UTM individual verificável",
            "privacy": "Somente contagens agregadas, sem telefones ou dados pessoais"
        },
        "registrations": len(unique),
        "uniquePhones": sum(x["has_phone"] for x in unique.values()),
        "groupJoins": None,
        "daily": [{"day": key, "registrations": value} for key, value in sorted(days.items())],
        "utmContents": [{"value": key, "registrations": value} for key, value in sorted(contents.items())],
        "byCampaign": [{"campaignId": cid, "registrations": count, "method": "utm_individual"} for cid, count in sorted(per_campaign.items())],
        "unattributedRegistrations": sum(x["broadcast"] is None for x in unique.values()),
    }


def run():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    credential = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not credential:
        LOG.warning("Credenciais da conta de serviço indisponíveis; resumo X1 anterior preservado.")
        return False
    try:
        session = sheets_session(credential)
        cols = fetch_columns(session)
        campaigns = json.loads(CAMPAIGNS.read_text(encoding="utf-8")).get("campaigns", [])
        now = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
        data = build_summary(cols, campaigns, now)
    except Exception as exc:  # optional X1 integration must not break UmClique sync
        LOG.warning("Não foi possível ler Captação com a conta de serviço (%s); verifique compartilhamento da planilha de origem.", type(exc).__name__)
        return False
    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    # Keep file stable when counts haven't changed, to avoid noisy deploys.
    clean = lambda doc: {key: value for key, value in doc.items() if key != "meta"}
    if clean(data) == clean(previous):
        LOG.info("Captação X1: %d cadastros; sem alteração desde a última sincronização.", data["registrations"])
        return False
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LOG.info("Captação X1 atualizada: %d cadastros, %d atribuíveis a disparos.",
             data["registrations"], sum(x["registrations"] for x in data["byCampaign"]))
    return True


if __name__ == "__main__":
    run()
