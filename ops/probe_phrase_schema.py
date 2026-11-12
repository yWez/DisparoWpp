"""Inspect message body FIELD SHAPES ONLY, never any customer content, ID or phone."""
import os,requests
from collections import Counter
base="https://api.umcliquedigital.com/functions/v1"
s=requests.Session();s.headers.update({"X-API-Key":os.environ["UMCLIQUE_API_KEY"],"Accept":"application/json"})
r=s.get(base+"/public-conversations",params={"status":"all","limit":100,"offset":0},timeout=25);r.raise_for_status()
rows=r.json().get("conversations",[])
inbound=0;sampled=0
for c in rows:
    if sampled>=12:break
    cid=c.get("id")
    if not cid:continue
    msg=s.get(base+"/public-conversations/messages",params={"conversation_id":cid,"limit":100,"offset":0},timeout=30);msg.raise_for_status()
    messages=msg.json().get("messages",[])
    candidates=[m for m in messages if m.get("is_from_me") is False]
    if not candidates:continue
    sampled+=1;inbound+=len(candidates)
    obj=candidates[0]
    known=("text","body","content","message","message_text","message_content","caption","payload","type","message_type","metadata","template","media")
    print("Inbound message field shapes:",{key:type(obj[key]).__name__ for key in known if key in obj})
    for key in known:
        if isinstance(obj.get(key),dict):
            nested=obj[key]
            print("Nested shapes",key,{k:type(nested[k]).__name__ for k in ("text","body","content","caption","message","text_body") if k in nested})
    break
print("Inspected inbound conversations:",sampled)
print("No message text, phone, contact or identifier printed.")
