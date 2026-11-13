import importlib.util
import pathlib
import unittest

HERE = pathlib.Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0,str(HERE / "scripts"))
spec = importlib.util.spec_from_file_location("sync_umclique", HERE / "scripts" / "sync_umclique.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class TestUmCliqueSync(unittest.TestCase):
    def setUp(self):
        self.item = {
            "id": "broadcast-123", "name": "Disparo 1 - Wes", "status": "completed",
            "total_contacts": 51, "sent_count": 51, "failed_count": 3,
            "delivered_count": 45, "read_count": 30, "responded_count": 6,
            "conversion_count": 2, "created_at": "2026-11-09T13:00:00Z",
            "started_at": "2026-11-09T13:05:00Z", "completed_at": "2026-11-09T13:20:00Z",
            "channels": [{"channel_id": "channel-1", "provider": "meta", "template_name": "convite_evento"}],
            "contacts_sample": [{"name": "Pessoa Teste", "phone": "+5583999000000"}]
        }
        self.now = "2026-11-11T18:00:00Z"

    def test_normalization_allowlist_and_timezone(self):
        row = sync.public_record(self.item)
        self.assertEqual(row["sent"], 51)
        self.assertEqual(row["failures"], 3)
        self.assertEqual(row["delivered"], 45)
        self.assertEqual(row["read"], 30)
        self.assertEqual(row["replied"], 6)
        self.assertEqual(row["status"], "Concluída")
        self.assertEqual(row["period"], "09/11/2026")
        self.assertNotIn("contacts_sample", row)
        self.assertNotIn("phone", str(row))
        self.assertNotIn("+5583999000000", str(row))

    def test_idempotent_update_same_id(self):
        new = sync.public_record(self.item)
        initial, modified, warnings = sync.merge_records([], [new], self.now)
        self.assertEqual(len(initial), 1)
        self.assertEqual(len(modified), 1)
        again, modified_again, warnings_again = sync.merge_records(initial, [new], self.now)
        self.assertEqual(len(again), 1)
        self.assertEqual(len(modified_again), 0)
        self.assertEqual(warnings + warnings_again, [])

    def test_safe_historical_matching(self):
        manual = [{"id":"D1", "name":"Disparo 1 - Wes", "contacts":51,"sent":51,
                   "failures":3,"note":"Conferido com print"}]
        normalized = sync.public_record(self.item)
        records, changed, warnings = sync.merge_records(manual, [normalized], self.now)
        self.assertEqual(len(records), 1)
        self.assertEqual(len(changed), 1)
        self.assertEqual(records[0]["campaignId"], "broadcast-123")
        self.assertEqual(records[0]["legacyId"], "D1")
        self.assertEqual(records[0]["note"], "Conferido com print")
        self.assertEqual(warnings, [])

    def test_legacy_wrong_date_is_quarantined(self):
        manual = [{"id":"D1","name":"Disparo 1 - Wes","contacts":51,"sent":51}]
        later = dict(self.item, created_at="2026-11-20T13:00:00Z", started_at=None)
        records, changed, warnings = sync.merge_records(manual, [sync.public_record(later)], self.now)
        self.assertEqual(len(records), 1)
        self.assertEqual(changed, [])
        self.assertEqual(len(warnings), 1)

    def test_sheet_row_header_total_and_manual(self):
        # Index 0 is the header at row 4. Row 24 is reserved for summary.
        values = [["Campanha","Nome"]] + [[""] for _ in range(30)]
        values[1] = ["09-10/11/2026", "Disparo 1 - Wes"] + [""]*10 + ["broadcast-123"]
        values[20] = ["TOTAL PERÍODO"]
        ids, names, blanks = sync.find_sheet_rows(values)
        self.assertEqual(ids["broadcast-123"], 5)
        self.assertIn(5,names["disparo 1 - wes"])
        self.assertNotIn(24,blanks)
        self.assertIn(12,blanks)

    def test_sheet_formulas_and_no_fake_zeros(self):
        record = sync.public_record(self.item)
        record["delivered"] = None
        vals = sync.sheet_values(record, 5)
        self.assertEqual(vals[3:6], [51,51,3])
        self.assertEqual(vals[15], "")
        self.assertIn('E5=""',vals[6])
        self.assertIn('F5=""',vals[7])

    def test_multiple_channels_deduplicate_by_campaign_id(self):
        class FakeSession:
            pass

        calls = []

        def fake_get(session, path, **params):
            calls.append(params["channel_id"])
            if params["channel_id"] == "ch-one":
                return {"broadcasts": [{"id":"a","name":"Disparo 1 - Wes"},
                                       {"id":"b","name":"Disparo 2 - Wes"}],
                        "next_offset":None}
            return {"broadcasts": [{"id":"b","name":"Disparo 2 - Wes"},
                                   {"id":"c","name":"Disparo 3 - Wes"}],
                    "next_offset":None}

        original = sync.get_json
        try:
            sync.get_json = fake_get
            result = sync.list_broadcasts(FakeSession(), "ch-one,ch-two",
                                          "2026-11-09T00:00:00-03:00")
        finally:
            sync.get_json = original
        self.assertEqual(calls, ["ch-one", "ch-two"])
        self.assertEqual([v["id"] for v in result], ["a", "b", "c"])

    def test_default_scope_imports_all_company_broadcasts(self):
        calls=[]
        original_get=sync.get_json
        try:
            def fake(session,path,**params):
                calls.append(params)
                return {"broadcasts":[
                    {"id":"meta-1","name":"Campanha Meta","channels":[{"provider":"meta"}]},
                    {"id":"qr-1","name":"Campanha QR","channels":[{"provider":"uazapi"}]},
                    {"id":"other-1","name":"Campanha sem canal"}
                ],"next_offset":None}
            sync.get_json=fake
            rows=sync.list_broadcasts(None,"","2026-11-09T00:00:00-03:00")
        finally:
            sync.get_json=original_get
        self.assertEqual(len(rows),3)
        self.assertNotIn("provider",calls[0])
        self.assertNotIn("channel_id",calls[0])

    def test_qr_provider_never_mislabeled_as_meta(self):
        qr=dict(self.item,channels=[{"channel_id":"qr-01","provider":"uazapi"}])
        row=sync.public_record(qr)
        self.assertEqual(row["provider"],"uazapi")
        self.assertEqual(row["channel"],"WhatsApp QR Code")
        vals=sync.sheet_values(row,17)
        self.assertEqual(vals[9],"WhatsApp QR Code")
        self.assertNotIn("contacts_sample",row)

    def test_unknown_provider_not_faked(self):
        no_channel=dict(self.item,channels=[])
        row=sync.public_record(no_channel)
        self.assertEqual(row["provider"],"unknown")
        self.assertEqual(row["channel"],"Provedor não informado")

    def test_discover_two_channels_for_seven_historical_campaigns(self):
        expected = [51, 50, 51, 150, 150, 150, 150]
        data = []
        for i, contacts in enumerate(expected, start=1):
            item = dict(self.item)
            item.update({
                "id": f"b-{i}",
                "name": f"Disparo {i} - Wes",
                "total_contacts": contacts,
                "created_at": "2026-11-10T15:00:00Z",
                "channels": [{
                    "channel_id": "channel-A" if i <= 3 else "channel-B",
                    "provider": "meta"
                }]
            })
            data.append(item)
        original = sync.get_json
        try:
            sync.get_json = lambda session, path, **kwargs: {
                "broadcasts": data, "next_offset": None
            }
            channels = sync.discover_channel_ids(None, "2026-11-09T00:00:00-03:00")
        finally:
            sync.get_json = original
        self.assertEqual(channels, ["channel-A", "channel-B"])

    def test_discover_fails_closed_on_missing_history(self):
        original = sync.get_json
        try:
            sync.get_json = lambda session, path, **kwargs: {
                "broadcasts": [self.item], "next_offset": None
            }
            with self.assertRaisesRegex(RuntimeError, "sete disparos"):
                sync.discover_channel_ids(None, "2026-11-09T00:00:00-03:00")
        finally:
            sync.get_json = original


    def test_d4_name_spacing_reconciles_manual_history(self):
        legacy = [{
            "id":"D4",
            "name":"Disparo 4 - Wes",
            "contacts":150,
            "sent":150,
            "failures":16
        }]
        api = dict(self.item,
            id="broadcast-d4",
            name="Disparo 4- Wes",
            total_contacts=150,
            sent_count=150,
            failed_count=16,
            created_at="2026-11-10T15:00:00Z",
            started_at="2026-11-10T15:05:00Z"
        )
        records, changed, warnings = sync.merge_records(
            legacy, [sync.public_record(api)], self.now
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["campaignId"], "broadcast-d4")
        self.assertEqual(records[0]["legacyId"], "D4")
        self.assertFalse(warnings)
        self.assertEqual(sync.canonical_name("Disparo 4- Wes"),
                         sync.canonical_name("Disparo 4 - Wes"))
        rows = [["Período","Campanha"]] + [[""] for _ in range(30)]
        rows[4] = ["10/11/2026","Disparo 4 - Wes"]
        _, by_name, _ = sync.find_sheet_rows(rows)
        self.assertEqual(by_name[sync.canonical_name("Disparo 4- Wes")], [8])

    def test_counts_invalid(self):
        self.assertIsNone(sync.as_count(None))
        with self.assertRaises(ValueError):
            sync.as_count(-1)
        with self.assertRaises(ValueError):
            sync.as_count("not a number")


if __name__ == "__main__":
    unittest.main()
