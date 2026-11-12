#!/usr/bin/env python3
"""UmClique inbox → private Sheets state → public aggregate mensageria dashboard.

Data minimization:
- Never stores message bodies, phones, lead names, contact/WhatsApp IDs in GitHub.
- Per-conversation technical state is persisted only in a restricted Google Sheet.
- Public output contains aggregate daily metrics and agent display names only.
- The lead's current assigned_agent_id, NOT message sender, owns the conversation.
- A run recomputes snapshots; no accumulation of duplicate events across runs.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import hmac
import json
import logging
import os
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
from requests.utils import quote
from sync_umclique import api_session, get_json
from luisa_campaign import RULE_VERSION, LABEL, incoming_match_days, contact_first_match, campaign_record_map

ROOT=Path(__file__).resolve().parent.parent
PUBLIC_FILE=ROOT/"data"/"mensageria.json"
API_TZ=ZoneInfo("America/Fortaleza")
SHEET_TITLE="Mensageria Estado"
SUMMARY_TITLE="Mensageria - Resumo"
CAMPAIGN_TITLE="Leads - Campanha Luisa"
HEADERS=["conversation_id","contact_key","channel_id","owner_id","modified_at",
         "created_at","status","unread_count","day_counts_json","observed_at",
         "message_count","complete_history","first_direction","last_direction",
         "first_inbound_day","last_inbound_day","last_outbound_day",
         "lp_scan_version","lp_match_first_day","lp_match_count"]
LOG=logging.getLogger("mensageria")
MAX_REFRESH=int(os.getenv("MENSAJERIA_MAX_REFRESH", "300"))
MAX_MESSAGES=int(os.getenv("MENSAJERIA_MAX_MESSAGES_PER_CONVERSATION", "4000"))
MIN_REFRESH_HOURS=int(os.getenv("MENSAJERIA_RESCAN_HOURS", "24"))
STATUSES={"active","archived"}
SHEET_ID=os.getenv("GOOGLE_SHEET_ID","").strip()

def utc_now():
    return dt.datetime.now(dt.timezone.utc)

def timestamp(raw):
    if not isinstance(raw,str) or not raw: return None
    try:
        parsed=dt.datetime.fromisoformat(raw.replace("Z","+00:00"))
        return parsed.astimezone(dt.timezone.utc) if parsed.tzinfo else None
    except ValueError:
        return None

def local_day(raw):
    parsed=timestamp(raw)
    return parsed.astimezone(API_TZ).date().isoformat() if parsed else None

def hash_key(api_key, value):
    if not value:return ""
    return hmac.new(api_key.encode(),str(value).encode(),"sha256").hexdigest()

def sanitize_name(value):
    # Attendant names only. Never call on contact names or message content.
    import re
    return re.sub(r"[\x00-\x1f<>]", " ", str(value or "")).strip()[:80]

def readonly(api,path,**params):
    return get_json(api,path,**params)

def list_conversations(api):
    rows=[];seen=set();offset=0;total=None
    for _ in range(1000):
        obj=readonly(api,"/public-conversations",status="all",limit=200,offset=offset)
        batch=obj.get("conversations")
        if not isinstance(batch,list):
            raise ValueError("Lista de conversas inválida")
        if isinstance(obj.get("total"),int):total=obj["total"]
        for item in batch:
            if not isinstance(item,dict) or not item.get("id"):continue
            cid=str(item["id"])
            if cid not in seen:
                rows.append(item);seen.add(cid)
        offset+=len(batch)
        if not batch or (total is not None and offset>=total) or len(batch)<200:break
    else:raise RuntimeError("Limite de paginação de conversas excedido")
    if total is not None and offset<total:
        raise RuntimeError("API não retornou todas as conversas")
    return rows,total if total is not None else len(rows)

def list_agents(api):
    result=readonly(api,"/public-agents")
    entries=result.get("agents")
    if not isinstance(entries,list):
        raise ValueError("Lista de atendentes inválida")
    out={}
    for x in entries:
        if isinstance(x,dict) and x.get("id"):
            out[str(x["id"])]={
                "key":hashlib.sha256(str(x["id"]).encode()).hexdigest()[:12],
                "name":sanitize_name(x.get("name")) or "Atendente sem nome",
                "active":x.get("is_active") if isinstance(x.get("is_active"),bool) else None
            }
    return out

def discovered_channels(conversations):
    """Derive channel identities from the authorized company inbox, not broadcast IDs.

    Aliases deliberately contain no phone number or lead names, since the
    published GitHub Pages dashboard is public.
    """
    import re
    known={"whatsapp_oficial":"WhatsApp Oficial",
           "meta":"WhatsApp Oficial","wapi":"WhatsApp WAPI",
           "uazapi":"WhatsApp UAZAPI"}
    result={}
    for item in conversations:
        if not isinstance(item,dict):continue
        channel_id=str(item.get("channel_id") or "")
        channel=item.get("channel") or {}
        if not isinstance(channel,dict):channel={}
        provider=str(channel.get("provider") or "").casefold()
        if not channel_id or provider not in known:continue
        # Stable non-reversible channel alias, not a contact phone number.
        alias=hashlib.sha256(channel_id.encode()).hexdigest()[:8]
        default=known[provider]+" · "+alias
        candidate=sanitize_name(channel.get("name") or channel.get("display_name") or "")
        if re.search(r"\d[\d\s()+.\-]{7,}",candidate):
            candidate=""
        result[channel_id]=candidate or default
    return result


def list_messages(api,cid):
    by_id={}; offset=0; total=None; missing=0
    for _ in range(max(1,(MAX_MESSAGES+199)//200)):
        result=readonly(api,"/public-conversations/messages",
                        conversation_id=cid,limit=200,offset=offset)
        batch=result.get("messages")
        if not isinstance(batch,list):raise ValueError("Resposta da lista de mensagens inválida")
        if isinstance(result.get("total"),int):total=result["total"]
        for message in batch:
            if not isinstance(message,dict):continue
            msg_id=message.get("id")
            if msg_id is None:continue
            if str(msg_id) not in by_id:by_id[str(msg_id)]=message
        offset+=len(batch)
        if not batch or (total is not None and offset>=total) or len(batch)<200:break
        if offset>=MAX_MESSAGES:break
    complete=total is not None and offset>=total or (total is None and len(batch)<200)
    return list(by_id.values()), bool(complete), total

def summarize_messages(messages,complete=True):
    """Aggregate one conversation only, without retaining message content or sender IDs."""
    entries=[];seen_dates=defaultdict(lambda:[0,0]);unknown_dates=0
    for m in messages:
        direction=m.get("is_from_me")
        if not isinstance(direction,bool):continue
        raw=m.get("timestamp") or m.get("sent_at") or m.get("created_at")
        day=local_day(raw)
        if not day:
            unknown_dates+=1
            continue
        when=timestamp(raw)
        idx=1 if direction else 0
        seen_dates[day][idx]+=1
        entries.append((when,idx))
    entries.sort(key=lambda x:x[0])
    inbound_days=[d for d,v in seen_dates.items() if v[0]]
    outbound_days=[d for d,v in seen_dates.items() if v[1]]
    return {
        "day_counts":{d:counts for d,counts in sorted(seen_dates.items())},
        "message_count":sum(sum(x) for x in seen_dates.values()),
        "complete_history":bool(complete and unknown_dates==0),
        "first_direction":"outbound" if entries and entries[0][1] else "inbound" if entries else "",
        "last_direction":"outbound" if entries and entries[-1][1] else "inbound" if entries else "",
        "first_inbound_day":min(inbound_days) if inbound_days else "",
        "last_inbound_day":max(inbound_days) if inbound_days else "",
        "last_outbound_day":max(outbound_days) if outbound_days else ""
    }

def google_session(secret):
    obj=json.loads(secret)
    if obj.get("type")!="service_account":raise ValueError("Credenciais Google inválidas")
    creds=service_account.Credentials.from_service_account_info(
        obj,scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return AuthorizedSession(creds)

def google_request(google,method,endpoint,**kwargs):
    resp=google.request(method,
        "https://sheets.googleapis.com/v4/spreadsheets/"+SHEET_ID+endpoint,
        timeout=60,**kwargs)
    resp.raise_for_status()
    return resp.json() if resp.content else {}

def ensure_tabs(google):
    meta=google_request(google,"GET","?fields=sheets(properties(sheetId,title,hidden,gridProperties(columnCount)))")
    names={x["properties"]["title"]:x["properties"]["sheetId"] for x in meta.get("sheets",[])}
    additions=[]
    if SHEET_TITLE not in names:
        additions.append({"addSheet":{"properties":{"title":SHEET_TITLE,"hidden":True,
            "gridProperties":{"rowCount":10000,"columnCount":len(HEADERS)}}}})
    if SUMMARY_TITLE not in names:
        additions.append({"addSheet":{"properties":{"title":SUMMARY_TITLE,
            "gridProperties":{"rowCount":2000,"columnCount":12}}}})
    if CAMPAIGN_TITLE not in names:
        additions.append({"addSheet":{"properties":{"title":CAMPAIGN_TITLE,
            "gridProperties":{"rowCount":10000,"columnCount":10}}}})
    for sheet in meta.get("sheets",[]):
        props=sheet.get("properties",{})
        if props.get("title")==SHEET_TITLE:
            current=props.get("gridProperties",{}).get("columnCount",0)
            if current<len(HEADERS):
                additions.append({"updateSheetProperties":{
                    "properties":{"sheetId":props["sheetId"],
                                  "gridProperties":{"columnCount":len(HEADERS)}},
                    "fields":"gridProperties.columnCount"}})
    if additions:
        google_request(google,"POST",":batchUpdate",json={"requests":additions})
    return names

def read_state(google):
    vals=google_request(google,"GET","/values/"+quote("'"+SHEET_TITLE+"'!A1:T10000",safe=""))
    rows=vals.get("values",[])
    if not rows:
        update_values(google,[(1,HEADERS)])
        return {}
    if rows[0]!=HEADERS:
        # Additive migration only: preserve every existing cell and row.
        if rows[0]==HEADERS[:17]:
            update_values(google,[(1,HEADERS)])
        else:
            raise ValueError("Cabeçalho do estado privado inesperado; não sobrescrever")
    found={}
    for line,row in enumerate(rows[1:],start=2):
        if not row or not row[0]:continue
        extended=(row+[""]*len(HEADERS))[:len(HEADERS)]
        entry=dict(zip(HEADERS,extended))
        entry["_sheetRow"]=line
        try: entry["day_counts"]=json.loads(entry.pop("day_counts_json") or "{}")
        except (TypeError,ValueError):raise ValueError("JSON de estado inválido na linha "+str(line))
        entry["complete_history"]=str(entry["complete_history"]).lower()=="true"
        entry["lp_match_count"]=int(entry.get("lp_match_count") or 0)
        found[str(entry["conversation_id"])]=entry
    return found

def update_values(google,positions):
    for start in range(0,len(positions),120):
        batch=positions[start:start+120]
        data=[{"range":f"'{SHEET_TITLE}'!A{index}:T{index}","values":[values]}
              for index,values in batch]
        google_request(google,"POST","/values:batchUpdate",
            json={"valueInputOption":"RAW","data":data})

def row_values(v):
    return [
        v.get("conversation_id",""),v.get("contact_key",""),v.get("channel_id",""),
        v.get("owner_id",""),v.get("modified_at",""),v.get("created_at",""),
        v.get("status",""),v.get("unread_count",0),
        json.dumps(v.get("day_counts",{}),ensure_ascii=False,separators=(",",":")),
        v.get("observed_at",""),v.get("message_count",0),
        str(bool(v.get("complete_history",False))).lower(),
        v.get("first_direction",""),v.get("last_direction",""),
        v.get("first_inbound_day",""),v.get("last_inbound_day",""),v.get("last_outbound_day",""),
        v.get("lp_scan_version",""),v.get("lp_match_first_day",""),v.get("lp_match_count",0)
    ]

def record_meta(conversation,api_key):
    contact=conversation.get("contact") or {}
    identity=contact.get("wa_id") or contact.get("phone") or contact.get("id") or conversation.get("contact_id")
    return {
        "conversation_id":str(conversation["id"]),
        "contact_key":hash_key(api_key,identity),
        "channel_id":str(conversation.get("channel_id") or ""),
        "owner_id":str(conversation.get("assigned_agent_id") or ""),
        "modified_at":str(conversation.get("updated_at") or ""),
        "created_at":str(conversation.get("created_at") or ""),
        "status":str(conversation.get("status") or ""),
        "unread_count":int(conversation.get("unread_count") or 0)
    }

def update_state(api,existing,conversations,api_key,allowed):
    """Update all assignment metadata; fetch message histories only if new/modified/stale."""
    fresh={};candidates=[];changes=set();now=utc_now();stamp=now.isoformat().replace("+00:00","Z")
    for convo in conversations:
        cid=str(convo.get("id") or "")
        if not cid:continue
        meta=record_meta(convo,api_key)
        if meta["channel_id"] not in allowed:
            continue
        prev=existing.get(cid,{})
        next_record={**prev,**meta}
        if not prev:
            next_record.update(day_counts={},message_count=0,complete_history=False,
                               first_direction="",last_direction="",observed_at="")
        fresh[cid]=next_record
        observed=timestamp(prev.get("observed_at"))
        stale=not observed or (now-observed).total_seconds()>(MIN_REFRESH_HOURS*3600)
        changed=not prev or prev.get("modified_at")!=meta["modified_at"]
        if not prev or changed or stale or not prev.get("complete_history") or prev.get("lp_scan_version")!=RULE_VERSION:
            candidates.append((0 if not prev.get("observed_at") else 1 if changed else 2,cid))
        if not prev or any(prev.get(k)!=meta.get(k) for k in meta):
            changes.add(cid)
    candidates.sort(key=lambda x:x[0])
    processed=0;failed=0
    for _,cid in candidates[:MAX_REFRESH]:
        messages,complete,total=list_messages(api,cid)
        snapshot=summarize_messages(messages,complete=complete)
        first_match, match_count=incoming_match_days(messages,local_day)
        fresh[cid].update(snapshot,observed_at=stamp,
                          lp_scan_version=RULE_VERSION,
                          lp_match_first_day=first_match,
                          lp_match_count=match_count)
        changes.add(cid)
        processed+=1
    return fresh,changes,processed,len(candidates),stamp

def safe_owner_key(owner_id):
    return hashlib.sha256(str(owner_id).encode()).hexdigest()[:12] if owner_id else "unassigned"

def name_map(agents,state):
    names={safe_owner_key(agent_id):v["name"] for agent_id,v in agents.items()}
    for item in state.values():
        id=item.get("owner_id")
        if id and safe_owner_key(id) not in names:
            names[safe_owner_key(id)]="Responsável não encontrado no cadastro"
    names["unassigned"]="Não atribuído"
    return names

def scoped_days(period,now_day):
    if period=="all":return None
    today=dt.date.fromisoformat(now_day)
    backward={"today":0,"yesterday":1,"7d":6,"30d":29}
    if period=="yesterday":
        d=today-dt.timedelta(days=1)
        return d.isoformat(),d.isoformat()
    days=backward[period]
    return (today-dt.timedelta(days=days)).isoformat(),today.isoformat()

def rollup(records,period,owner,channel,now_day,include_waiting=False):
    dates=scoped_days(period,now_day)
    inbound=outbound=unread=conversations=initiated=waiting=0
    contacts_inbound=set();contacts_all=set()
    for r in records:
        if owner!="all" and r["owner_key"]!=owner:continue
        if channel!="all" and r["channel_id"]!=channel:continue
        if not r.get("observed_at"):continue
        per_day=r.get("day_counts") or {}
        in_count=out_count=0
        for day,arr in per_day.items():
            if dates and not dates[0]<=day<=dates[1]:continue
            in_count+=int(arr[0])
            out_count+=int(arr[1])
        if in_count+out_count==0:continue
        conversations+=1
        inbound+=in_count;outbound+=out_count
        key=r.get("contact_key")
        if key:
            contacts_all.add(key)
            if in_count:contacts_inbound.add(key)
        if r.get("first_direction")=="inbound" and (not dates or
             (r.get("first_inbound_day") and dates[0]<=r["first_inbound_day"]<=dates[1])):
            initiated+=1
        if r.get("status")=="active" and r.get("last_direction")=="inbound":
            # 'Última mensagem é recebida' rather than an SLA/overdue claim.
            if not dates or (r.get("last_inbound_day") and dates[0]<=r["last_inbound_day"]<=dates[1]):
                waiting+=1
        unread+=int(r.get("unread_count") or 0) if period=="all" else 0
    return {"inbound":inbound,"outbound":outbound,
            "conversations":conversations,"contactsWithInbound":len(contacts_inbound),
            "contactsInConversations":len(contacts_all),
            "firstInboundConversations":initiated,
            "lastInboundActiveConversations":waiting,
            "unread":unread if period=="all" else None}

def make_public(state,agents,channels,source_total,now):
    owner_names=name_map(agents,state)
    owner_keys=sorted(set(owner_names)|{safe_owner_key(a) for a in agents})
    owner_ids=["all"]+owner_keys
    channel_ids=["all"]+sorted(channels)
    records=[]
    for r in state.values():
        if r.get("channel_id") not in channels:continue
        item={**r,"owner_key":safe_owner_key(r.get("owner_id"))}
        records.append(item)
    processed=sum(bool(x.get("observed_at")) for x in records)
    missing=[x for x in records if not x.get("complete_history")]
    all_complete=processed==len(records) and not missing and len(records)>0
    day=now.astimezone(API_TZ).date().isoformat()
    # Exact unique contact counts for fixed periods and filters, computed privately.
    rollups=[]
    for period in ("all","today","yesterday","7d","30d"):
        for owner in owner_ids:
            for channel in channel_ids:
                values=rollup(records,period,owner,channel,day)
                rollups.append({"period":period,"owner":owner,"channel":channel,**values})
    # One day/owner/channel cell, aggregated without IDs, fully filterable in browser.
    daily_raw=defaultdict(lambda:{"inbound":0,"outbound":0,"contacts":set(),"conversations":set()})
    for r in records:
        if not r.get("observed_at"):continue
        for d,arr in (r.get("day_counts") or {}).items():
            for owner in ("all",r["owner_key"]):
                for channel in ("all",r["channel_id"]):
                    cell=daily_raw[(d,owner,channel)]
                    cell["inbound"]+=int(arr[0]);cell["outbound"]+=int(arr[1])
                    if int(arr[0]) and r.get("contact_key"):cell["contacts"].add(r["contact_key"])
                    if sum(int(v) for v in arr):cell["conversations"].add(r["conversation_id"])
    daily=[
        {"day":day,"owner":owner,"channel":channel,
         "inbound":cell["inbound"],"outbound":cell["outbound"],
         "inboundContacts":len(cell["contacts"]),
         "conversations":len(cell["conversations"])}
        for (day,owner,channel),cell in sorted(daily_raw.items())
    ]
    # Display all registered agents (including zero conversations), plus Unassigned.
    activity_by_key={safe_owner_key(agent_id):agent.get("active") for agent_id,agent in agents.items()}
    owner_list=[{"key":key,"name":name, "active":activity_by_key.get(key)}
        for key,name in sorted(owner_names.items(),key=lambda x:x[1].casefold())]
    return {
        "meta":{
            "schemaVersion":1,"lastSyncedAt":now.isoformat().replace("+00:00","Z"),
            "timeZone":"America/Fortaleza",
            "source":"UmClique /public-conversations, /messages e /public-agents",
            "allAccountConversations":source_total,
            "inScopeConversations":len(records),"scannedConversations":processed,
            "completeConversations":sum(bool(x.get("complete_history")) for x in records),
            "complete":all_complete,
            "dataState":"completo" if all_complete else "parcial",
            "ownerRule":"assigned_agent_id atual da conversa (não autor de cada mensagem)",
            "coverageNote":"Durante o primeiro carregamento, totais representam apenas conversas inspecionadas.",
            "privacyNote":"Nenhum conteúdo, telefone ou identificação de lead é publicado.",
            "dateMeaning":"Dia de envio/recebimento da mensagem no fuso America/Fortaleza",
            "channelScope":"Todos os canais WhatsApp da conta empresarial autenticada; IDs de conversas não são os IDs dos broadcasts",
            "caveats":[
                "Mensagens enviadas na caixa de entrada podem incluir templates de disparo; não somar diretamente com o dashboard de campanhas.",
                "Atribuição por responsável representa a carteira atual, não quem digitou ou enviou cada mensagem.",
                "Uma pessoa pode aparecer em diferentes canais ou conversas; deduplicação usa identificadores reconhecidos pela API.",
                "Primeira mensagem recebida é a primeira observada no histórico; não comprova origem espontânea nem conversão de campanha.",
                "A área pública expõe somente números agregados e nomes dos atendentes, jamais conteúdos ou telefones."
            ]
        },
        "owners":owner_list,
        "channels":[{"id":cid,"name":channels[cid]} for cid in sorted(channels)],
        "rollups":rollups,"daily":daily
    }

def public_summary_sheet(google,payload):
    head=["Responsável atual","Canal","Entrantes (mensagens)","Saídas (mensagens)",
          "Contatos distintos que escreveram","Conversas com mensagens",
          "Primeira mensagem recebida","Última mensagem recebida (ativas)",
          "Cobertura","Atualizado em"]
    owner_name={x["key"]:x["name"] for x in payload["owners"]}
    channel_name={x["id"]:x["name"] for x in payload["channels"]}
    rows=[head]
    for r in payload["rollups"]:
        if r["period"]!="all" or r["owner"]=="all" or r["channel"]!="all":continue
        rows.append([
            owner_name.get(r["owner"],"Não identificado"),"Todos os canais",
            r["inbound"],r["outbound"],r["contactsWithInbound"],r["conversations"],
            r["firstInboundConversations"],r["lastInboundActiveConversations"],
            payload["meta"]["dataState"],payload["meta"]["lastSyncedAt"]])
    rows.append(["TOTAL","Todos",*[
        next(r for r in payload["rollups"] if r["period"]=="all" and r["owner"]=="all" and r["channel"]=="all")[k]
        for k in ("inbound","outbound","contactsWithInbound","conversations",
                  "firstInboundConversations","lastInboundActiveConversations")],
        payload["meta"]["dataState"],payload["meta"]["lastSyncedAt"]])
    target="/values/"+quote("'"+SUMMARY_TITLE+"'!A1:J2000",safe="")
    google_request(google,"PUT",target,params={"valueInputOption":"RAW"},
                   json={"values":rows})
    if len(rows)<2000:
        start=len(rows)+1
        google_request(google,"POST","/values/"+quote(f"'{SUMMARY_TITLE}'!A{start}:J2000",safe="")+":clear",
                       json={})

def run():
    logging.basicConfig(level=logging.INFO,format="%(levelname)s %(message)s")
    api_key=os.environ["UMCLIQUE_API_KEY"]
    google_secret=os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    if not SHEET_ID:raise RuntimeError("GOOGLE_SHEET_ID não configurado")
    if not 1<=MAX_REFRESH<=1000 or not 200<=MAX_MESSAGES<=20000:
        raise ValueError("Limites de mensageria inválidos")
    api=api_session(api_key)
    agents=list_agents(api)
    conversations,total=list_conversations(api)
    # Company-scoped conversation IDs differ from broadcast Meta IDs. Never
    # join these two identifier namespaces or arbitrarily attribute messages
    # to broadcast numbers. Include only WhatsApp providers returned for this
    # authorized company account.
    channel_info=discovered_channels(conversations)
    if not channel_info:
        raise RuntimeError("Nenhum canal WhatsApp empresarial localizado nas conversas")
    google=google_session(google_secret)
    ensure_tabs(google)
    existing=read_state(google)
    fresh,changed,refreshed,candidates,stamp=update_state(
        api,existing,conversations,api_key,set(channel_info))
    next_index=max([r.get("_sheetRow",1) for r in existing.values()]+[1])+1
    changes=[]
    for cid in sorted(changed):
        record=fresh[cid]; row=existing.get(cid,{}).get("_sheetRow")
        if row is None:
            row=next_index;next_index+=1
        changes.append((row,row_values(record)))
    if changes:
        update_values(google,changes)
    payload=make_public(fresh,agents,channel_info,total,utc_now())
    public_summary_sheet(google,payload)
    PUBLIC_FILE.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    LOG.info("Conversations in account: %d | LP Crypto in scope: %d | inspected: %d | updated in this run: %d | pending refresh: %d",
             total,payload["meta"]["inScopeConversations"],
             payload["meta"]["scannedConversations"],refreshed,max(0,candidates-refreshed))
    if path:=os.getenv("GITHUB_STEP_SUMMARY"):
        all_rollup=next(r for r in payload["rollups"] if r["period"]=="all" and r["owner"]=="all" and r["channel"]=="all")
        with open(path,"a",encoding="utf-8") as out:
            out.write(
                "\n### Mensageria UmClique\n"
                f"- Conversas no escopo: {payload['meta']['inScopeConversations']}\n"
                f"- Conversas inspecionadas: {payload['meta']['scannedConversations']}\n"
                f"- Conversas processadas nesta execução: {refreshed}\n"
                f"- Cobertura: {payload['meta']['dataState']}\n"
                f"- Mensagens recebidas nas conversas processadas: {all_rollup['inbound']}\n"
                f"- Mensagens enviadas nas conversas processadas: {all_rollup['outbound']}\n"
                "- Conteúdos, telefones e IDs de clientes não são publicados.\n"
            )

if __name__=="__main__":
    run()
