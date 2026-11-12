import unittest
import datetime as dt
import json
import pathlib
import sys

ROOT=pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"scripts"))
from luisa_campaign import (
    RULE_VERSION,LABEL,has_luisa_greeting,incoming_match_days,
    contact_first_match,aggregate_campaign)
from sync_mensageria import local_day,scoped_days,make_public,row_values,HEADERS

class CampaignAttributionTests(unittest.TestCase):
    def test_exact_and_variants(self):
        for value in [
            "Oi, equipe Luisa Pires",
            "OI equipe LUÍSA PIRES!!!",
            "Olá, equipe Luisa Pires, gostaria de conhecer o relatório.",
            "Boa tarde equipe Luisa Pires!",
            "Oi equipe Luisa Pires, tenho dúvidas",
        ]:
            self.assertTrue(has_luisa_greeting(value),value)
    def test_reject_mentions_and_noncampaign(self):
        for value in [
            "Você conhece a equipe Luisa Pires?",
            "Vou enviar o texto Oi equipe Luisa Pires",
            "Oi, equipe Ana Pires",
            "Oi Luisa, equipe aqui",
            None,
            {"text":"Oi equipe Luisa Pires"}
        ]:
            self.assertFalse(has_luisa_greeting(value),str(value))
    def test_only_inbound_and_deduped_ids(self):
        messages=[
            {"id":"1","is_from_me":False,"content":"Oi, equipe Luisa Pires",
             "timestamp":"2026-11-12T02:00:00Z"},
            {"id":"1","is_from_me":False,"content":"Oi, equipe Luisa Pires",
             "timestamp":"2026-11-12T02:00:00Z"},
            {"id":"2","is_from_me":True,"content":"Oi, equipe Luisa Pires",
             "timestamp":"2026-11-12T03:00:00Z"},
            {"id":"3","is_from_me":False,"content":"Olá, equipe Luisa Pires",
             "timestamp":"2026-11-12T11:00:00Z"}
        ]
        first,count=incoming_match_days(messages,local_day)
        self.assertEqual(first,"2026-11-11")
        self.assertEqual(count,2)
        # Text is not returned by the detector.
        self.assertNotIn("Luisa",str((first,count)))

    def build(self,contact,conv,owner,first,dates,modified="2026-11-12T13:00:00Z"):
        return {
            "conversation_id":conv,"contact_key":contact,
            "channel_id":"chA","owner_id":owner,"owner_key":owner,
            "modified_at":modified,"observed_at":"2026-11-12T14:00:00Z",
            "complete_history":True,"lp_scan_version":RULE_VERSION,
            "lp_match_first_day":first,"lp_match_count":1 if first else 0,
            "day_counts":dates,"status":"active",
            "first_direction":"inbound","last_direction":"outbound",
            "first_inbound_day":first,"last_inbound_day":first
        }
    def test_unique_lead_multiple_conversations_and_owner(self):
        one=self.build("hashA","c1","Wes","2026-11-11",{"2026-11-11":[1,0]})
        two=self.build("hashA","c2","Ana","2026-11-12",{"2026-11-12":[2,1]},"2026-11-12T18:00:00Z")
        three=self.build("hashB","c3","Ana","",{"2026-11-12":[2,2]})
        result=aggregate_campaign([one,two,three],
                    ["all","Wes","Ana"],["all","chA"],"2026-11-12",scoped_days)
        rows=result["public"]["rollups"]
        total=next(x for x in rows if x["period"]=="all" and x["owner"]=="all" and x["channel"]=="all")
        self.assertEqual(total["identifiedLeads"],1)
        self.assertEqual(total["inboundFromLeads"],3)
        self.assertEqual(total["outboundToLeads"],1)
        self.assertEqual(total["markedConversations"],2)
        ana=next(x for x in rows if x["period"]=="all" and x["owner"]=="Ana" and x["channel"]=="all")
        self.assertEqual(ana["identifiedLeads"],1)
        wes=next(x for x in rows if x["period"]=="all" and x["owner"]=="Wes" and x["channel"]=="all")
        self.assertEqual(wes["identifiedLeads"],0)
        today=next(x for x in rows if x["period"]=="today" and x["owner"]=="all" and x["channel"]=="all")
        self.assertEqual(today["identifiedLeads"],0)
        self.assertEqual(today["inboundFromLeads"],2)
        self.assertEqual(result["public"]["coverage"]["scannedConversations"],3)
        self.assertNotIn("hashA",json.dumps(result["public"]))
        self.assertNotIn("c1",json.dumps(result["public"]))
    def test_missing_version_excluded_from_coverage(self):
        r=self.build("hash","conv","Wes","",{})
        r["lp_scan_version"]=""
        output=aggregate_campaign([r],["all","Wes"],["all","chA"],"2026-11-12",scoped_days)
        self.assertFalse(output["public"]["coverage"]["complete"])
        self.assertEqual(output["public"]["coverage"]["scannedConversations"],0)
    def test_private_storage_columns_and_public_privacy(self):
        self.assertEqual(len(HEADERS),20)
        r=self.build("sensitive-hash","conversation-secret","Wes","2026-11-11",{"2026-11-11":[1,2]})
        r["first_direction"]="inbound"
        r["lp_match_count"]=2
        cells=row_values(r)
        self.assertEqual(len(cells),len(HEADERS))
        self.assertEqual(cells[-2],"2026-11-11")
        self.assertEqual(cells[-1],2)
        pub=make_public({"conversation-secret":r},
            {"Wes":{"name":"Wes","active":True}},
            {"chA":"Canal A"},1,
            dt.datetime(2026,11,12,15,tzinfo=dt.timezone.utc))
        body=json.dumps(pub)
        self.assertEqual(pub["campaign"]["rollups"][0]["identifiedLeads"],1)
        self.assertNotIn("conversation-secret",body)
        self.assertNotIn("sensitive-hash",body)

if __name__=="__main__":
    unittest.main()
