"""Regressions for the LP Crypto campaign tables and five-minute cadence."""
import pathlib
import re
import unittest

ROOT=pathlib.Path(__file__).resolve().parent.parent

def read(path):
    return (ROOT/path).read_text(encoding="utf-8")

class LayoutAndCadenceTests(unittest.TestCase):
    def test_two_long_campaign_tables_do_not_force_grid_overflow(self):
        css=read("assets/mensageria.css")
        self.assertRegex(css,r"\.campaign-columns\s*\{[^}]*grid-template-columns:\s*minmax\(0,1fr\)")
        self.assertRegex(css,r"\.campaign-columns>div\s*\{[^}]*min-width:0")
        self.assertRegex(css,r"\.campaign-columns table\s*\{[^}]*table-layout:fixed")
        self.assertIn("overflow-wrap:break-word",css)

    def test_mobile_rows_have_accessible_labels(self):
        js=read("assets/mensageria.js")
        css=read("assets/mensageria.css")
        self.assertIn('cell.dataset.label=',js)
        self.assertIn('td[data-label]::before',css)
        self.assertIn("max-width:700px",css)
        self.assertIn("overflow-x:auto",css)

    def test_site_shows_last_successful_data_refresh(self):
        html=read("mensageria.html")
        js=read("assets/mensageria.js")
        for identifier in ('id="freshnessState"','id="lastUpdated"','id="coverageCount"'):
            self.assertIn(identifier,html)
        self.assertIn('ageMinutes>15',js)
        self.assertIn("Dados desatualizados",js)
        self.assertIn('window.setInterval(()=>{if(document.visibilityState!=="hidden")load();},60000)',js)

    def test_fast_fallback_and_full_pipeline_retained(self):
        workflow=read(".github/workflows/sync-umclique.yml")
        fast=read(".github/workflows/sync-campaigns-fast.yml")
        scheduler=read("ops/agendador-externo-apps-script.gs")
        self.assertIn('cron: "17,47 * * * *"',workflow)
        self.assertIn('cron: "3-59/5 * * * *"',fast)
        self.assertIn('everyMinutes(j.minutes)',scheduler)
        self.assertIn("minutes:5",scheduler)
        self.assertIn("minutes:15",scheduler)
        self.assertIn("GITHUB_ACTIONS_TOKEN",scheduler)
        self.assertNotIn("ghp_",scheduler)
        # The original campaigns/X1/messaging paths and secrets remain intact.
        for must in ("scripts/sync_umclique.py","scripts/sync_x1.py",
                     "scripts/sync_mensageria.py","UMCLIQUE_API_KEY",
                     "GOOGLE_SERVICE_ACCOUNT_JSON","GH_PAGES_PUSH_TOKEN",
                     "group: umclique-sync"):
            self.assertIn(must,workflow)
        self.assertIn("group: umclique-sync",fast)
        self.assertIn("python scripts/sync_x1.py",fast)
        self.assertIn("data/disparos.json data/x1-attribution.json",fast)
        self.assertIn("X1_GROUP_SHEET_ID",fast)

if __name__=="__main__":
    unittest.main()
