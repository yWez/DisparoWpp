"""Importação privada de listas verificadas de membros dos grupos X1.

Duas abas privadas recebem um telefone por linha (A8:A). Só são consideradas
quando o administrador informa a data da conferência e muda B3 para
LISTA_VERIFICADA. Um snapshot comprova presença NA DATA DA CONFERÊNCIA;
não comprova data de ingresso ou atribuição ao disparo. Nenhum telefone ou
JID de participante entra no JSON público.
"""
from __future__ import annotations

import requests


ROSTER_SOURCES = (
    {"tab": "Membros X1 - Mesa 22",
     "groupId": "120363413061600324@g.us",
     "label": "Mesa 22/11 - Black LP"},
    {"tab": "Membros X1 - Mesa 17-19-22",
     "groupId": "120363412992839319@g.us",
     "label": "Mesa 17, 19 e 22/11 - Black LP"},
)
VALID_EVIDENCE = {"lista_participantes", "exportacao_grupo"}


def _scalar(value_range):
    values = value_range.get("values") or []
    return str(values[0][0]).strip() if values and values[0] else ""


def fetch_roster_sheets(session, sheet_id, parse_time):
    """Get private rows in one batch. Never log or publish raw member lists."""
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values:batchGet"
    ranges = []
    for src in ROSTER_SOURCES:
        title = src["tab"].replace("'", "''")
        for cell in ("B1", "B2", "B3", "B4", "A8:A"):
            ranges.append(("ranges", f"'{title}'!{cell}"))
    try:
        res = session.get(url, params=ranges, timeout=(12, 40))
        res.raise_for_status()
        parts = res.json().get("valueRanges") or []
    except (requests.RequestException, ValueError):
        return None
    if len(parts) != len(ROSTER_SOURCES)*5:
        return None
    rosters = []
    for i, source in enumerate(ROSTER_SOURCES):
        group, checked, status, evidence = [_scalar(parts[5*i+j]) for j in range(4)]
        raw = parts[5*i+4].get("values") or []
        valid = (group == source["groupId"]
                 and status.casefold() == "lista_verificada"
                 and evidence.casefold() in VALID_EVIDENCE
                 and parse_time(checked) is not None)
        rosters.append({
            "groupId": source["groupId"], "label": source["label"],
            "checkedAt": checked if valid else None, "verified": valid,
            "phones": [str(x[0]).strip() for x in raw if x and str(x[0]).strip()] if valid else []
        })
    return rosters


def _normalize_roster_phone(value, normalize_phone):
    """Accept Brazilian phone/JID; reject anonymous LID/opaque identities."""
    original = str(value or "").strip()
    local = original.split("@", 1)[0].split(":", 1)[0]
    if "@" in original and not original.endswith(("@s.whatsapp.net", "@c.us")):
        return None
    digits = normalize_phone(local)
    if digits and len(digits) in (10,11):
        digits = "55" + digits
    if not digits or not (digits.startswith("55") and len(digits) in (12,13)):
        return None
    return digits


def roster_summary(rosters, registrations, normalize_phone, parse_time):
    """Public aggregate matches, not proven joins.

    Missing source, partial roster, or unidentifiable numbers never generate
    imaginary entries. No contact-level information leaves this function.
    """
    if rosters is None:
        return {
            "groupMembers": None, "groupMemberRate": None,
            "groupRosterStatus": "unavailable", "groupRosterCheckedAt": None,
            "groupRosterCounts": [], "rosterUnmatched": None
        }
    eligible = {r["phone"] for r in registrations.values() if r.get("phone")}
    checked_groups = 0
    matched = set()
    per_group = []
    verified_dates = []
    for roster in rosters:
        if not roster["verified"]:
            continue
        group_phones = set()
        for raw in roster["phones"]:
            number = _normalize_roster_phone(raw, normalize_phone)
            if number:
                group_phones.add(number)
        if not group_phones:
            continue
        checked_groups += 1
        group_matches = eligible & group_phones
        matched.update(group_matches)
        dt_obj = parse_time(roster["checkedAt"])
        verified_dates.append(dt_obj)
        per_group.append({
            "group": roster["label"],
            "membersInRoster": len(group_phones),
            "x1MembersMatched": len(group_matches),
            "checkedAt": dt_obj.isoformat()
        })
    status = ("unavailable" if checked_groups == 0 else
              "verified" if checked_groups == len(ROSTER_SOURCES) else "partial")
    return {
        "groupMembers": len(matched) if checked_groups else None,
        "groupMemberRate": (len(matched) / len(eligible)
                            if status=="verified" and eligible else None),
        "groupRosterStatus": status,
        "groupRosterCheckedAt": max(verified_dates).isoformat() if verified_dates else None,
        "groupRosterCounts": per_group,
        "rosterUnmatched": (len(eligible - matched) if status=="verified" else None)
    }
