"""Conservative, privacy-preserving identification of the LP Crypto WhatsApp greeting.

The text of a message is examined in-memory and immediately discarded.
Only the date of first matching inbound message and a count are retained.
Matching this text is a strong SIGNAL, not proof of campaign attribution.
"""
import re
import unicodedata

RULE_VERSION="lp-phrase-v1"
LABEL="Oi, equipe Luisa Pires"
START=re.compile(
    r"^(?:oi|ola|bom dia|boa tarde|boa noite)[\s,.!?:;-]*"
    r"equipe[\s,.!?:;-]+luisa[\s,.!?:;-]+pires\b",
    flags=re.IGNORECASE
)

def normalized(value):
    if not isinstance(value,str):
        return ""
    return "".join(char for char in unicodedata.normalize("NFKD",value.casefold())
                   if unicodedata.category(char)!="Mn").strip()

def has_luisa_greeting(value):
    # Only at the start of the message, to avoid unrelated quotations/mid-text hits.
    return bool(START.search(normalized(value)[:180]))

def incoming_match_days(messages,local_day):
    """Return (first_day, number of messages matching greeting) without text."""
    hits=[]
    seen=set()
    for m in messages:
        if not isinstance(m,dict) or m.get("is_from_me") is not False:
            continue
        identifier=m.get("id")
        if identifier is None or str(identifier) in seen:
            continue
        seen.add(str(identifier))
        content=m.get("content")
        if not has_luisa_greeting(content):
            continue
        day=local_day(m.get("timestamp") or m.get("sent_at") or m.get("created_at"))
        if day:
            hits.append(day)
    return min(hits) if hits else "",len(hits)

def contact_first_match(records):
    """Earliest first matching day across every conversation sharing a contact hash."""
    result={}
    for row in records:
        if not row.get("observed_at") or not row.get("lp_match_first_day"):
            continue
        key=row.get("contact_key")
        if not key: continue
        day=row["lp_match_first_day"]
        result[key]=min(day,result.get(key,day))
    return result

def campaign_record_map(records):
    """An identified contact's conversations all count toward their message activity."""
    first=contact_first_match(records)
    return [r for r in records if r.get("contact_key") in first and r.get("observed_at")],first
