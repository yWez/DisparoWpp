"""Private X1 roster reconciliation. Fixtures contain synthetic numbers only."""
import json
import pathlib
import sys
import unittest
from unittest.mock import Mock

ROOT=pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"scripts"))
from sync_x1 import build_summary, fetch_member_rosters, summarize_member_rosters

ID="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
def columns():
    return (
        [["2026-11-09 10:00:00"],["2026-11-10 11:00:00"],["2026-11-11 12:00:00"]],
        [["5583999991111"],["5583888882222"],["5583777773333"]],
        [["whatsapp","x1",ID,ID],["whatsapp","x1","","x1-base"],["whatsapp","x1","","x1-base"]],
    )

class SnapshotX1Test(unittest.TestCase):
    def test_private_import_requires_approval(self):
        response=Mock(status_code=200)
        response.json.return_value={"valueRanges":[
            {"values":[["120363111@g.us"],["2026-11-13 19:30:00"],["PENDENTE"],["lista_participantes"],["Gr 1"]]},
            {"values":[["5583999991111"],["5583888882222"]]},
            {"values":[["120363222@g.us"],["2026-11-13 20:30:00"],["LISTA_VERIFICADA"],["lista_participantes"],["Gr 2"]]},
            {"values":[["(83) 99999-1111"],["5583777773333"]]},
        ]}
        session=Mock()
        session.get.return_value=response
        rosters=fetch_member_rosters(session)
        self.assertEqual(len(rosters),1)
        self.assertEqual(rosters[0]["alias"],"Mesa da Luisa 17/19/22")
        self.assertEqual(rosters[0]["phones"],{"5583999991111","5583777773333"})
        self.assertEqual(len(session.get.call_args.kwargs["params"]),4)

    def test_roster_overlap_not_double_counted_and_not_group_join(self):
        rosters=[
            {"alias":"Mesa da Luisa 22/11","checked":"2026-11-13T10:00:00-03:00","phones":{"5583999991111","5583888882222"},"group_id":"120363111@g.us"},
            {"alias":"Mesa da Luisa 17/19/22","checked":"2026-11-13T11:00:00-03:00","phones":{"5583999991111","5583777773333","5511999999999"},"group_id":"120363222@g.us"},
        ]
        data=build_summary(columns(),[{"campaignId":ID}],"2026-11-13T19:00:00Z",
                           member_rosters=rosters)
        self.assertEqual(data["registrations"],3)
        self.assertEqual(data["groupMembersVerified"],3)
        self.assertEqual(data["groupMemberRate"],1.0)
        self.assertIsNone(data["groupJoins"]) # snapshot != proof of entry date
        self.assertEqual(data["byCampaign"][0]["groupMembersVerified"],1)
        self.assertEqual(data["memberGroups"][0]["x1Present"],2)
        self.assertEqual(data["memberGroups"][1]["x1Present"],2)
        self.assertEqual(data["meta"]["memberStatus"],"verified")
        raw=json.dumps(data)
        for secret in ("5583999991111","5583888882222","5583777773333","120363111@g.us"):
            self.assertNotIn(secret,raw)

    def test_pended_import_is_not_zero(self):
        data=build_summary(columns(),[{"campaignId":ID}],"2026-11-13T19:00:00Z",
                           member_rosters=None)
        self.assertIsNone(data["groupMembersVerified"])
        self.assertIsNone(data["groupMemberRate"])
        self.assertEqual(data["meta"]["memberStatus"],"unavailable")

    def test_verified_snapshot_without_match_is_valid_zero(self):
        roster=[{"alias":"Mesa da Luisa 22/11","checked":"2026-11-13T13:00:00-03:00","phones":{"5511999998888"},"group_id":"120363111@g.us"}]
        data=build_summary(columns(),[{"campaignId":ID}],"now",member_rosters=roster)
        self.assertEqual(data["groupMembersVerified"],0)
        self.assertEqual(data["groupMemberRate"],0)
        self.assertEqual(data["groupJoins"],None)

if __name__=="__main__":unittest.main()
