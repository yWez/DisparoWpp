import collections
import hashlib
import json
import os
import requests

BASE="https://api.umcliquedigital.com/functions/v1"
key=os.environ["UMCLIQUE_API_KEY"]
s=requests.Session();s.headers.update({"X-API-Key":key,"Accept":"application/json"})
api_allowed=json.load(open("data/disparos.json"))["channels"]
allowed={str(c["id"]) for c in api_allowed if c.get("provider")=="meta"}
rsp=s.get(BASE+"/public-channels",timeout=30);rsp.raise_for_status()
public_channels=rsp.json().get("channels",[])
known={str(c.get("id")):c for c in public_channels}
count=collections.Counter(); shapes={}
offset=0
for page in range(50):
    r=s.get(BASE+"/public-conversations",params={"status":"all","limit":200,"offset":offset},timeout=45)
    r.raise_for_status();obj=r.json(); batch=obj.get("conversations",[])
    for row in batch:
        channel=str(row.get("channel_id") or "")
        nested=row.get("channel") if isinstance(row.get("channel"),dict) else {}
        contact=row.get("contact") if isinstance(row.get("contact"),dict) else {}
        count[channel]+=1
        shapes[channel]={"nestedKeys":sorted(k for k in nested if k in {"id","name","provider","type","status","channel_id","phone_number_id","instance_id"}),
                         "nestedIdMatches":str(nested.get("id")) in allowed,
                         "nestedChannelIdMatches":str(nested.get("channel_id")) in allowed,
                         "contactIdMatches":str(contact.get("channel_id")) in allowed,
                         "known":channel in known,
                         "allowed":channel in allowed,
                         "provider":str(nested.get("provider") or known.get(channel,{}).get("provider") or "unknown")[:22]}
    offset+=len(batch)
    if offset>=obj.get("total",offset) or len(batch)<200:break
def alias(cid):
    if not cid:return "(ausente)"
    return hashlib.sha256(cid.encode()).hexdigest()[:8]
print("Total de conversas de empresa consultadas:",sum(count.values()))
print("Canais do broadcast Meta autorizados:",len(allowed))
print("Canais presentes em /public-channels:",len(public_channels))
print("Canais de conversa distintos:",len(count))
print("Resumo de correspondência (somente quantidades):")
print(json.dumps({
 "iguais_a_meta_broadcast":sum(v for k,v in count.items() if k in allowed),
 "iguais_a_lista_public_channels":sum(v for k,v in count.items() if k in known),
 "outros":sum(v for k,v in count.items() if k and k not in allowed),
 "sem_channel_id":count.get("",0)
},ensure_ascii=False))
for cid,n in count.most_common(12):
    print("channel hash:",alias(cid),"conversations:",n,"schema:",json.dumps(shapes[cid],ensure_ascii=False))
print("Somente aliases de canal e nomes de campos foram usados; nada de mensagens, telefones ou IDs brutos.")
