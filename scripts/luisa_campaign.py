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


def aggregate_campaign(records,owners,channels,now_day,scoped_days):
    """Aggregate leads uniquely, using owner/channel of latest matching conversation.

    The same contact can have several conversations: a lead is counted once.
    Message activity of this contact across their conversations is attributed
    to the owner/channel of their latest modified *matching* conversation.
    """
    from collections import defaultdict
    grouped=defaultdict(list)
    for r in records:
        if r.get("contact_key") and r.get("observed_at"):
            grouped[r["contact_key"]].append(r)
    leads={}
    for key,convos in grouped.items():
        matched=[r for r in convos if r.get("lp_match_first_day")]
        if not matched:continue
        rep=max(matched,key=lambda r:(str(r.get("modified_at") or ""),str(r.get("conversation_id") or "")))
        activity=defaultdict(lambda:[0,0])
        for r in convos:
            for day,counts in (r.get("day_counts") or {}).items():
                activity[day][0]+=int(counts[0]);activity[day][1]+=int(counts[1])
        leads[key]=dict(
            first=min(r["lp_match_first_day"] for r in matched),
            owner=rep.get("owner_key") or "unassigned",
            channel=rep.get("channel_id") or "",
            activity=activity,markedConversations=len(matched))
    def subset(period,owner,channel):
        days=scoped_days(period,now_day)
        unique=active=matched_convs=inbound=outbound=0
        for v in leads.values():
            if owner!="all" and v["owner"]!=owner:continue
            if channel!="all" and v["channel"]!=channel:continue
            if not days or days[0]<=v["first"]<=days[1]:
                unique+=1;matched_convs+=v["markedConversations"]
            inc=out=0
            for day,n in v["activity"].items():
                if days and not days[0]<=day<=days[1]:continue
                inc+=n[0];out+=n[1]
            inbound+=inc;outbound+=out
            if inc:active+=1
        return {"identifiedLeads":unique,"markedConversations":matched_convs,
                "activeLeads":active,"inboundFromLeads":inbound,
                "outboundToLeads":outbound}
    rollups=[{"period":period,"owner":owner,"channel":channel,
              **subset(period,owner,channel)}
             for period in ("all","today","yesterday","7d","30d")
             for owner in owners for channel in channels]
    daily_raw=defaultdict(lambda:{"fresh":set(),"active":set(),"inbound":0,"outbound":0})
    for key,lead in leads.items():
        for day in set(lead["activity"])|{lead["first"]}:
            msg=lead["activity"].get(day,[0,0])
            for owner in ("all",lead["owner"]):
                for channel in ("all",lead["channel"]):
                    cell=daily_raw[(day,owner,channel)]
                    if day==lead["first"]:cell["fresh"].add(key)
                    if msg[0]:cell["active"].add(key)
                    cell["inbound"]+=msg[0];cell["outbound"]+=msg[1]
    daily=[{"day":day,"owner":owner,"channel":channel,
            "identifiedLeads":len(v["fresh"]),"activeLeads":len(v["active"]),
            "inboundFromLeads":v["inbound"],"outboundToLeads":v["outbound"]}
           for (day,owner,channel),v in sorted(daily_raw.items())]
    scanned=sum(bool(r.get("observed_at")) and r.get("lp_scan_version")==RULE_VERSION
                and r.get("complete_history") for r in records)
    return {
        "public":{
            "marker":LABEL,
            "method":"Sinal de origem por saudação recebida; não comprova atribuição de mídia",
            "coverage":{"scannedConversations":scanned,"inScopeConversations":len(records),
                        "complete":bool(records) and scanned==len(records)},
            "rollups":rollups,"daily":daily
        },
        "private":leads
    }
