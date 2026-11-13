"""Read-only API audit: no contact records, tokens or telephone numbers logged."""
import collections
import datetime
import os
import sys
sys.path.insert(0, "scripts")
from sync_umclique import api_session, get_json, local_date
api=api_session(os.environ["UMCLIQUE_API_KEY"])
def pages(params):
    offset=0;found={};provider=collections.Counter()
    for _ in range(15):
        data=get_json(api,"/public-broadcasts",limit=100,offset=offset,**params)
        batch=data.get("broadcasts",[])
        if not isinstance(batch,list):raise ValueError("Bad broadcast response")
        for item in batch:
            if not isinstance(item,dict) or not item.get("id"):continue
            found[str(item["id"])]=item
        nxt=data.get("next_offset")
        if nxt is None or nxt is False:break
        offset=int(nxt)
    return found
created="2026-11-09T00:00:00-03:00"
unfiltered=pages({"created_from":created})
meta=pages({"created_from":created,"provider":"meta"})
print("API company broadcast count (all providers):",len(unfiltered))
print("API Meta-only broadcast count:",len(meta))
print("Additional non-Meta-or-unknown campaigns:",len(set(unfiltered)-set(meta)))
by_date=collections.Counter()
by_providers=collections.Counter()
for c in unfiltered.values():
    when=local_date(c.get("created_at") or c.get("started_at"))
    by_date[when.date().isoformat() if when else "unknown"]+=1
    for ch in c.get("channels") or []:
        by_providers[str(ch.get("provider") or "unknown")]+=1
print("By local date:",dict(sorted(by_date.items())))
print("Channels by provider:",dict(sorted(by_providers.items())))
for c in sorted(unfiltered.values(),key=lambda x:x.get("created_at") or "",reverse=True)[:12]:
    when=local_date(c.get("created_at") or c.get("started_at"))
    print("Recent broadcast:",(when.isoformat()[:16] if when else "unknown"),
          "name",str(c.get("name") or "")[:100],
          "status",str(c.get("status") or "?")[:24],
          "sent",c.get("sent_count"))
print("Read-only audit completed; no contacts or identifiers logged.")
