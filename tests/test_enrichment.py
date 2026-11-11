import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"scripts"))
from enrichment import sanitize_errors, sanitize_channel_list, assign_origins, clean_text

class EnrichmentTest(unittest.TestCase):
    def test_error_groups_exclude_sensitive_examples(self):
        payload={"broadcast_id":"x","summary":{"failed_total":7,"truncated":True,"scanned_rows":150},
                 "groups":[{"key":"131049","code":"131049","title":"Entrega bloqueada pela Meta",
                            "description":"Erro com telefone +5583999999999",
                            "raw_examples":["Dado secreto: 83999999999"],
                            "sample":["********9999"],"count":7,"explained":True}]}
        x=sanitize_errors(payload)
        self.assertEqual(x["groups"][0]["count"],7)
        self.assertEqual(x["summary"]["failedTotal"],7)
        self.assertTrue(x["summary"]["truncated"])
        self.assertNotIn("sample",x["groups"][0])
        self.assertNotIn("raw_examples",x["groups"][0])
        self.assertNotIn("83999999999",str(x))
        self.assertIn("dado omitido",str(x))

    def test_unknown_error_kept_unclassified(self):
        x=sanitize_errors({"summary":{},"groups":[{"code":"999999","title":"Erro especial","count":4}]})
        self.assertEqual(x["groups"][0]["recoverability"],"Revisão manual")
        self.assertEqual(x["groups"][0]["type"],"Outros/não classificados")

    def test_missing_error_report_is_not_zero(self):
        self.assertIsNone(sanitize_errors({}))

    def test_channel_allowlist(self):
        source={"channels":[
         {"id":"a","name":"Meta LP Crypto","status":"connected","phone_number_id":"123456789"},
         {"id":"b","name":"Outro","status":"connected","phone_number_id":"098765432"}]}
        visible=sanitize_channel_list(source,["a"])
        self.assertEqual(len(visible),1)
        self.assertEqual(visible[0]["name"],"Meta LP Crypto")
        self.assertNotIn("phone_number_id",str(visible))

    def test_origin_requires_approved_taxonomy(self):
        rows=[{"campaignId":"c1"},{"campaignId":"c2"}]
        mapped=assign_origins(rows,{"c1":"PDF Instagram","c2":"Origem imaginada"})
        self.assertEqual(mapped[0]["campaignOrigin"],"PDF Instagram")
        self.assertIsNone(mapped[1]["campaignOrigin"])

if __name__=="__main__":
    unittest.main()
