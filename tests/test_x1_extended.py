"""Real X1 semantics: first chronological registration, witnessed group joins, UTMs."""
import datetime as dt
import json
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"scripts"))
from sync_x1 import (build_summary, local_registration_time, verified_joins,
                     unique_registrations, fetch_group_events, normalize_phone)


CID="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
OTHER="bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
def row(ts, phone, campaign="x1-base", content="x1-base", source="whatsapp", medium="x1"):
    return [[ts],[phone],[source,medium,campaign,content]]

def merge(rows):
    return tuple([[r[k] for r in rows] for k in range(3)])

class X1ExtendedTests(unittest.TestCase):
    def setUp(self):
        self.campaigns=[{"campaignId":CID},{"campaignId":OTHER}]
        self.base=merge([
            row("2026-11-12 15:00:00","+55 (83) 99999-9999","x1-base","x1-base"),
            row("2026-11-09 10:00:00","5583999999999","x1-"+CID,"x1-"+CID),
            row("2026-11-10 10:00:00","5583888888888"),
            row("2026-11-09 11:00:00","5583777777777",source="instagram",medium="pago"),
        ])
    def test_deduplicates_by_chronological_first_even_out_of_order(self):
        x=build_summary(self.base,self.campaigns,"2026-11-13T22:00:00Z")
        self.assertEqual(x["registrations"],2)
        self.assertEqual(x["uniquePhones"],2)
        self.assertEqual(x["duplicatesRemoved"],1)
        self.assertEqual(x["x1RowsFound"],3)
        self.assertEqual(x["daily"],[
            {"day":"2026-11-09","registrations":1},
            {"day":"2026-11-10","registrations":1}])
        self.assertEqual(x["byCampaign"][0]["campaignId"],CID)
        self.assertEqual(x["byCampaign"][0]["registrations"],1)
        self.assertEqual(x["unattributedRegistrations"],1)
        self.assertEqual(x["attributionCoverage"],0.5)
        self.assertEqual(x["meta"]["lastCheckedAt"],"2026-11-13T22:00:00Z")
    def test_real_group_joins_require_approved_evidence(self):
        events=[
            ["2026-11-12 10:30:00","+55 (83) 99999-9999","group1","lista_participantes","confirmado",CID],
            ["2026-11-12 10:30:00","5583999999999","group1","lista_participantes","confirmado",CID],
            ["2026-11-13 12:00:00","5583888888888","group1","evento_entrada","pendente",""],
            ["2026-11-13 12:00:00","5583000000000","group1","verificacao_manual","confirmado",""],
            ["2026-11-13 12:00:00","5583888888888","group1","","confirmado",""],
        ]
        x=build_summary(self.base,self.campaigns,"now",events)
        self.assertEqual(x["groupJoins"],1)
        self.assertEqual(x["groupJoinRate"],0.5)
        self.assertEqual(x["groupJoinDaily"],[{"day":"2026-11-12","joins":1}])
        self.assertEqual(x["byCampaign"][0]["groupJoins"],1)
        self.assertEqual(x["meta"]["groupStatus"],"verified")
    def test_no_group_source_or_empty_tab_is_not_zero(self):
        for events in (None,[],[["2026-11-12 15:00:00","5583999999999","group1","", "confirmado",""]]):
            x=build_summary(self.base,self.campaigns,"now",events)
            self.assertIsNone(x["groupJoins"])
            self.assertIsNone(x["groupJoinDaily"])
            self.assertIsNone(x["groupJoinRate"])
            self.assertEqual(x["meta"]["groupStatus"],"unavailable")
    def test_unverified_link_click_is_not_group_member(self):
        x=build_summary(self.base,self.campaigns,"now",[
            ["2026-11-12 15:00:00","5583999999999","group1","clique_convite","confirmado",""]])
        self.assertIsNone(x["groupJoins"])
    def test_conflicting_utm_cannot_attrib_campaign(self):
        entries=merge([row("2026-11-10 10:00:00","5583999999999",CID,OTHER)])
        x=build_summary(entries,self.campaigns,"now")
        self.assertEqual(x["byCampaign"],[])
        self.assertEqual(x["unattributedRegistrations"],1)
    def test_timezone_conversion_determines_local_day(self):
        when=local_registration_time("2026-11-13T01:30:00Z")
        self.assertEqual(when.date().isoformat(),"2026-11-12")
        date=local_registration_time("10/11/2026 12:45:15")
        self.assertEqual(date.date().isoformat(),"2026-11-10")
    def test_no_phone_kept_as_unidentifiable_registration(self):
        entries=merge([row("2026-11-10 10:00:00",""),row("2026-11-10 10:05:00","")])
        x=build_summary(entries,self.campaigns,"now")
        self.assertEqual(x["registrations"],2)
        self.assertEqual(x["uniquePhones"],0)
        self.assertEqual(x["registrationsWithoutPhone"],2)
        self.assertIsNone(x["groupJoinRate"])
    def test_json_has_no_personal_values(self):
        x=build_summary(self.base,self.campaigns,"now",[
            ["2026-11-12 10:30:00","5583999999999","private-group-id","verificacao_manual","confirmado",CID]])
        txt=json.dumps(x)
        for secret in ("5583999999999","private-group-id","5583888888888"):
            self.assertNotIn(secret,txt)
    def test_missing_tab_cannot_appear_as_zero(self):
        class NoTab:
            def get(self,*args,**kwargs):
                class Response:
                    status_code=400
                    text="Unable to parse range: 'Entradas Grupo X1'"
                return Response()
        self.assertIsNone(fetch_group_events(NoTab()))

if __name__=="__main__":
    unittest.main()
