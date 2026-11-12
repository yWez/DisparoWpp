import pathlib
import sys
import json
import unittest
from unittest.mock import patch
import datetime as dt

ROOT=pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"scripts"))
import sync_mensageria as s

class InboxMetricsTest(unittest.TestCase):
    def setUp(self):
        self.messages=[
            {"id":"m1","is_from_me":False,"timestamp":"2026-11-11T02:05:00Z",
             "content":"Privado +5583999990000"},
            {"id":"m2","is_from_me":True,"timestamp":"2026-11-11T02:09:00Z"},
            {"id":"m3","is_from_me":False,"timestamp":"2026-11-11T16:00:00Z"}
        ]
    def test_local_day_crosses_utc_midnight(self):
        self.assertEqual(s.local_day(self.messages[0]["timestamp"]),"2026-11-10")
        self.assertEqual(s.local_day(self.messages[2]["timestamp"]),"2026-11-11")
    def test_direction_and_histogram(self):
        x=s.summarize_messages(self.messages)
        self.assertTrue(x["complete_history"])
        self.assertEqual(x["day_counts"]["2026-11-10"],[1,1])
        self.assertEqual(x["day_counts"]["2026-11-11"],[1,0])
        self.assertEqual(x["first_direction"],"inbound")
        self.assertEqual(x["last_direction"],"inbound")
        self.assertNotIn("Privado",json.dumps(x))
    def test_missing_timestamp_marks_incomplete(self):
        x=s.summarize_messages([{"id":"m1","is_from_me":False}])
        self.assertFalse(x["complete_history"])
        self.assertEqual(x["message_count"],0)
    def test_pagination_dedup_by_message_id(self):
        def fake(api,path,**kwargs):
            if kwargs["offset"]==0:
                return {"messages":[{"id":"1","is_from_me":False,"timestamp":"2026-11-11T13:00:00Z"}],
                        "total":1}
            raise AssertionError("Page should not repeat")
        with patch.object(s,"readonly",fake):
            rows,complete,total=s.list_messages(None,"abc")
        self.assertEqual(len(rows),1)
        self.assertTrue(complete)
        self.assertEqual(total,1)
    def test_owner_is_current_assignee(self):
        conv={"id":"conv-1","assigned_agent_id":"agent-X","channel_id":"ch",
              "contact":{"wa_id":"5583999999999"}}
        meta=s.record_meta(conv,"secret")
        self.assertEqual(meta["owner_id"],"agent-X")
        self.assertNotIn("5583999999999",str(meta))
        self.assertNotIn("phone",meta)
    def test_rollup_deduplicates_contacts_across_conversations(self):
        base={"contact_key":"contact-hash","channel_id":"ch","status":"active",
              "owner_key":"owner","observed_at":"2026-11-11T18:00:00Z",
              "first_direction":"inbound","last_direction":"inbound",
              "last_inbound_day":"2026-11-11","first_inbound_day":"2026-11-11",
              "unread_count":0}
        records=[
            dict(base,conversation_id="a",day_counts={"2026-11-11":[2,1]}),
            dict(base,conversation_id="b",day_counts={"2026-11-11":[3,2]})
        ]
        r=s.rollup(records,"today","all","all","2026-11-11")
        self.assertEqual(r["inbound"],5)
        self.assertEqual(r["outbound"],3)
        self.assertEqual(r["contactsWithInbound"],1)
        self.assertEqual(r["conversations"],2)
        self.assertEqual(r["lastInboundActiveConversations"],2)
    def test_public_output_has_only_aggregates(self):
        agents={"agent-X":{"key":s.safe_owner_key("agent-X"),"name":"Carol","active":True},
                "agent-Y":{"key":s.safe_owner_key("agent-Y"),"name":"Ana","active":True}}
        state={"conv-1":{"conversation_id":"conv-1","contact_key":"secret-contact-hash",
            "channel_id":"ch","owner_id":"agent-X","observed_at":"2026-11-11T18:00:00Z",
            "complete_history":True,"day_counts":{"2026-11-11":[1,2]},"status":"active",
            "first_direction":"inbound","last_direction":"outbound",
            "first_inbound_day":"2026-11-11","last_inbound_day":"2026-11-11"}}
        now=dt.datetime(2026,11,11,22,0,tzinfo=dt.timezone.utc)
        data=s.make_public(state,agents,{"ch":"Canal A"},1,now)
        body=json.dumps(data)
        self.assertNotIn("conv-1",body)
        self.assertNotIn("secret-contact-hash",body)
        self.assertNotIn("phone",body)
        self.assertEqual(len(data["owners"]),3) # two agents + unassigned
        self.assertTrue(data["meta"]["complete"])
        self.assertEqual(s.rollup([dict(state["conv-1"],owner_key=s.safe_owner_key("agent-X"))],
           "all","all","all","2026-11-11")["inbound"],1)
        self.assertTrue(any(d["owner"]=="all" and d["channel"]=="all" for d in data["daily"]))
    def test_partial_coverage_explained(self):
        state={"c":{"conversation_id":"c","contact_key":"hash","channel_id":"ch",
              "owner_id":"","day_counts":{},"status":"active",
              "observed_at":"","complete_history":False}}
        data=s.make_public(state,{},{"ch":"Canal"},1,s.utc_now())
        self.assertFalse(data["meta"]["complete"])
        self.assertEqual(data["meta"]["dataState"],"parcial")
        self.assertEqual(data["meta"]["scannedConversations"],0)

if __name__=="__main__":
    unittest.main()
