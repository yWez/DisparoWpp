#!/usr/bin/env python3
"""Schema-only diagnostics for the authorized UmClique API. Never prints source values.

This intentionally emits fixed-key presence/types only; message contents, contact
names, telephone numbers and IDs never appear in CI logs.
"""
import os
import sys
import requests

API = "https://api.umcliquedigital.com/functions/v1"
KEY = os.getenv("UMCLIQUE_API_KEY")
if not KEY:
    sys.exit("Missing UMCLIQUE_API_KEY secret")
s = requests.Session()
s.headers.update({"X-API-Key":KEY,"Accept":"application/json"})
HEAD = ("id","name","contact","contacts","assigned_to","assigned_user","assignee",
        "responsible","responsible_id","responsavel","responsavel_id","owner","owner_id",
        "user","user_id","agent","agent_id","assigned_at","last_message",
        "messages","conversations","conversation_id","status","channel_id",
        "channel","team","team_id","unread_count","created_at","updated_at",
        "timestamp","sent_at","message_date","is_from_me","from_me","direction",
        "date","sent_by","sender","total","limit","offset","next_offset",
        "page","pagination","data","items","phone","wa_id","contact_id")
ALLOW=set(HEAD)
def summary(obj):
    if isinstance(obj, dict):
        return "object:{"+", ".join(k+":"+typename(obj[k]) for k in HEAD if k in obj)+"}"
    if isinstance(obj,list):
        return "array["+str(len(obj))+"] "+(summary(obj[0]) if obj else "empty")
    return typename(obj)
def typename(value):
    if value is None:return "null"
    if isinstance(value,bool):return "bool"
    if isinstance(value,list):return "array["+str(len(value))+"]"
    if isinstance(value,dict):return "object"
    if isinstance(value,int):return "integer"
    if isinstance(value,str):return "string"
    return type(value).__name__
def get(endpoint, params):
    try:
        resp=s.get(API+endpoint,params=params,timeout=(10,25))
        print("Endpoint "+endpoint+": HTTP "+str(resp.status_code))
        if not resp.ok: return None
        obj=resp.json()
        print("Root "+summary(obj))
        if isinstance(obj,dict):
            for key in ("conversations","data","items","contacts","messages"):
                if isinstance(obj.get(key),list):
                    print("List "+key+" count of first page: "+str(len(obj[key])))
                    if obj[key]:
                        record=obj[key][0]
                        print("First row "+summary(record))
                        if isinstance(record,dict):
                            for nested in ("contact","assigned_user","assigned_to",
                                           "responsible","owner","agent","last_message","user"):
                                if isinstance(record.get(nested),dict):
                                    print("First row "+nested+": "+summary(record[nested]))
                        return (obj,record)
        return (obj,None)
    except (requests.RequestException,ValueError) as exc:
        print("Endpoint error: "+type(exc).__name__)
        return None
convs=get("/public-conversations",{"status":"all","limit":5,"offset":0})
if convs and convs[1] and convs[1].get("id"):
    get("/public-conversations/messages",
        {"conversation_id":convs[1]["id"],"limit":5,"offset":0})
get("/public-contacts",{"limit":3,"offset":0})
print("Schema-only inspection completed; no raw records or IDs logged.")
