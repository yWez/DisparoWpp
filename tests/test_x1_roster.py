"""Private roster imports: a verified member snapshot is not a proven X1 entry."""
import json
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"scripts"))
from sync_x1 import build_summary, local_registration_time, normalize_phone
from x1_roster import ROSTER_SOURCES, fetch_roster_sheets, roster_summary


def cols():
    return (
        [["2026-11-09 10:00:00"], ["2026-11-10 10:00:00"], ["2026-11-11 10:00:00"]],
        [["5511999991111"], ["5511999992222"], ["5511999993333"]],
        [["whatsapp","x1","","x1-base"]]*3
    )


def sample_roster(index, numbers, verified=True):
    spec=ROSTER_SOURCES[index]
    return {"groupId":spec["groupId"],"label":spec["label"],
            "checkedAt":"2026-11-13 21:30:00","verified":verified,
            "phones":list(numbers)}


class VerifiedRosterTests(unittest.TestCase):
    def test_partial_roster_only_reports_matches_not_group_joins(self):
        summary=build_summary(cols(),[], "2026-11-13T22:00:00Z",
                              group_rosters=[sample_roster(0, ["+55 11 99999-1111",
                                                              "5511999991111", "5511999999999"]),
                                             sample_roster(1, [],False)])
        self.assertEqual(summary["groupMembers"],1)
        self.assertEqual(summary["groupRosterStatus"],"partial")
        self.assertIsNone(summary["groupMemberRate"])
        self.assertIsNone(summary["rosterUnmatched"])
        self.assertIsNone(summary["groupJoins"])
        self.assertEqual(summary["groupRosterCounts"][0]["membersInRoster"],2)
        self.assertEqual(summary["groupRosterCounts"][0]["x1MembersMatched"],1)
        self.assertEqual(summary["meta"]["schemaVersion"],3)

    def test_fully_verified_two_groups_dedup_across_rosters(self):
        summary=build_summary(cols(),[],"now",group_rosters=[
            sample_roster(0,["5511999991111","5511999992222"]),
            sample_roster(1,["5511999991111","5511999993333","5511999993333"])])
        self.assertEqual(summary["groupMembers"],3)
        self.assertEqual(summary["groupMemberRate"],1)
        self.assertEqual(summary["rosterUnmatched"],0)
        self.assertEqual(summary["groupRosterStatus"],"verified")
        self.assertEqual(len(summary["groupRosterCounts"]),2)
        self.assertIsNone(summary["groupJoins"])
        exported=json.dumps(summary)
        for phone in ("5511999991111","5511999992222","5511999993333"):
            self.assertNotIn(phone,exported)

    def test_pending_empty_or_missing_roster_is_unavailable(self):
        summary=build_summary(cols(),[],"now",group_rosters=[
            sample_roster(0,["5511999991111"],False),
            sample_roster(1,[],True)
        ])
        self.assertIsNone(summary["groupMembers"])
        self.assertEqual(summary["groupRosterStatus"],"unavailable")
        self.assertIsNone(summary["rosterUnmatched"])
        self.assertIsNone(summary["groupJoins"])

    def test_group_snapshot_cannot_prove_join_after_signup(self):
        src=ROSTER_SOURCES[0]["groupId"]
        group_events=[["2026-11-12 10:00:00","5511999991111",src,
                       "lista_participantes","confirmado",""]]
        summary=build_summary(cols(),[],"now",group_events,
                              [sample_roster(0,["5511999991111"]),sample_roster(1,[],False)])
        self.assertIsNone(summary["groupJoins"])
        self.assertEqual(summary["groupMembers"],1)

    def test_real_join_before_registration_excluded(self):
        summary=build_summary(cols(),[],"now",[
            ["2026-11-08 10:00:00","5511999991111",ROSTER_SOURCES[0]["groupId"],
             "evento_entrada","confirmado",""]
        ])
        self.assertIsNone(summary["groupJoins"])
        summary=build_summary(cols(),[],"now",[
            ["2026-11-12 10:00:00","5511999991111",ROSTER_SOURCES[0]["groupId"],
             "evento_entrada","confirmado",""]
        ])
        self.assertEqual(summary["groupJoins"],1)

    def test_jid_normalized_opaque_lid_rejected(self):
        summary=build_summary(cols(),[],"now",group_rosters=[
            sample_roster(0,["5511999991111@s.whatsapp.net", "2123123@lid", "5511999992222:17@s.whatsapp.net"]),
            sample_roster(1,[],False)
        ])
        self.assertEqual(summary["groupMembers"],2)

    def test_api_validates_sheet_status_and_group_id(self):
        parts=[]
        for i,roster in enumerate(ROSTER_SOURCES):
            parts.extend([
                {"values":[[roster["groupId"]]]},
                {"values":[["2026-11-13 21:30:00"]]},
                {"values":[["LISTA_VERIFICADA" if i==0 else "PENDENTE"]]},
                {"values":[["lista_participantes"]]},
                {"values":[["5511999991111"]]}
            ])
        class DummyResponse:
            def raise_for_status(self):pass
            def json(self):return {"valueRanges":parts}
        class DummySession:
            def get(self,url,params,timeout):
                assert len(params)==10
                assert "/values:batchGet" in url
                return DummyResponse()
        data=fetch_roster_sheets(DummySession(),"sheet-id",local_registration_time)
        self.assertTrue(data[0]["verified"])
        self.assertFalse(data[1]["verified"])
        self.assertEqual(len(data[1]["phones"]),0)

if __name__=="__main__":
    unittest.main()
