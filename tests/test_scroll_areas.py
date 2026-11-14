"""Regression checks: bounded lists keep the full dataset and accessible scrolling."""
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parent.parent
def load(name):
    return (ROOT/name).read_text(encoding="utf-8")

class ScrollAreasTests(unittest.TestCase):
    def test_both_pages_import_shared_assets(self):
        for html in ("index.html","mensageria.html"):
            data=load(html)
            self.assertIn('href="./assets/scroll-areas.css"',data)
            self.assertIn('src="./assets/scroll-areas.js"',data)
            self.assertLess(data.index('scroll-areas.css'),data.index('</head>'))
            self.assertLess(data.index('scroll-areas.js'),data.index('</body>'))

    def test_bounded_scrollers_include_campaign_and_message_tables(self):
        css=load("assets/scroll-areas.css")
        for selector in (".table-wrap",".v2-table-scroll",".table-scroll",
                         ".bar-list",".ratebars",".channel-list"):
            self.assertIn(selector,css)
        self.assertIn("max-height:min(var(--lp-scroll-height),66vh)",css)
        self.assertIn("max-height:min(335px,54vh)",css)
        self.assertIn("overscroll-behavior",css)
        self.assertIn("position:sticky",css)
        self.assertIn("top:0",css)

    def test_scroll_help_has_counts_and_accessible_keyboard_region(self):
        js=load("assets/scroll-areas.js")
        for fragment in ("countRows(el)","tbody.rows","lp-scroll-count",
                         "lp-scroll-tip","el.tabIndex=0",
                         '"role","region"','"aria-label"',
                         "ResizeObserver", "MutationObserver"):
            self.assertIn(fragment,js)

    def test_data_fetch_and_exports_unchanged(self):
        js=load("assets/scroll-areas.js")
        for forbidden in ("fetch(", "localStorage", "send(", "API_KEY", "Authorization"):
            self.assertNotIn(forbidden,js)
        self.assertIn("id=\"exportCsv\"",load("index.html"))
        self.assertIn("id=\"luisaCsv\"",load("mensageria.html"))
        self.assertIn('id="ownerCsv"',load("mensageria.html"))

    def test_mobile_cards_and_hints(self):
        css=load("assets/scroll-areas.css")
        self.assertIn("max-width:700px",css)
        self.assertIn(".campaign-columns .table-scroll{overflow-x:hidden}",css)
        self.assertIn(".lp-scroll-foot",css)

if __name__=="__main__":unittest.main()
