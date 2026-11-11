"""Privacy-safe attribution tests: real names and phones are not part of fixtures."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
from sync_x1 import build_summary, campaign_from_utm, normalize_phone


class X1Tests(unittest.TestCase):
    ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    def test_filters_x1_and_deduplicates_contacts(self):
        rows = (
            [["2026-11-09 10:00:00"], ["2026-11-09 11:00:00"],
             ["2026-11-10 14:00:00"], ["2026-11-10 15:00:00"]],
            [["5511999991111"], ["+55 (11) 99999-1111"], ["5511988882222"], ["5511977773333"]],
            [["whatsapp", "x1", "", "x1-base"],
             ["whatsapp", "x1", "", "x1-base"],
             ["meta", "pago", "", "BF26-VID-X1_mais-esperto"],
             ["whatsapp", "x1", "", "x1-" + self.ID[:8]]],
        )
        summary = build_summary(rows, [{"campaignId": self.ID}], "2026-11-11T21:00:00Z")
        self.assertEqual(summary["registrations"], 2)
        self.assertEqual(summary["uniquePhones"], 2)
        self.assertIsNone(summary["groupJoins"])
        self.assertEqual(summary["unattributedRegistrations"], 1)
        self.assertEqual(summary["byCampaign"][0]["campaignId"], self.ID)
        self.assertEqual(summary["byCampaign"][0]["registrations"], 1)
        self.assertEqual(summary["daily"], [{"day": "2026-11-09", "registrations": 1},
                                            {"day": "2026-11-10", "registrations": 1}])

    def test_generic_utm_cannot_attribute_broadcast(self):
        self.assertIsNone(campaign_from_utm("x1-base", "", [self.ID]))
        self.assertIsNone(campaign_from_utm("BF26-VID-X1_mais-esperto", "", [self.ID]))

    def test_exact_utm_can_attribute_single_campaign(self):
        self.assertEqual(campaign_from_utm("x1-" + self.ID, "", [self.ID]), self.ID)
        self.assertEqual(campaign_from_utm("", self.ID, [self.ID]), self.ID)
        self.assertEqual(normalize_phone("+55 (11) 99999-1111"), "5511999991111")


if __name__ == "__main__":
    unittest.main()
