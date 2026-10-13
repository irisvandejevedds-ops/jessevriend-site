import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build  # noqa: E402


def make(files):
    d = pathlib.Path(tempfile.mkdtemp())
    for name, data in files.items():
        p = d / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data))
    build.ROOT = d
    return d


class Render(unittest.TestCase):
    def tearDown(self):
        build.ROOT = ROOT

    def test_the_real_content_builds_and_has_the_apps(self):
        html, public = build.render()
        self.assertIn("Alberich", html)
        self.assertIn("https://tadpole.jessevriend.com/demo/", html)
        self.assertIn("Being and Becoming", html)

    def test_empty_sections_are_left_out(self):
        make({"content/site.json": {"name": "Jesse"}})
        html, _ = build.render()
        for gone in ('id="about"', 'id="projects"', 'id="pagers"', 'id="writing"', 'id="links"', 'id="bb"'):
            self.assertNotIn(gone, html)
        self.assertIn("<h1>Jesse</h1>", html)

    def test_text_is_escaped_and_dangerous_links_dropped(self):
        make({"content/site.json": {"name": "<script>alert(1)</script>", "about": "hi <b>x</b> [bad](javascript:alert(1)) [good](https://example.com/a?b=1&c=2)"}})
        html, _ = build.render()
        self.assertNotIn("<script>", html)
        self.assertNotIn("javascript:", html)
        self.assertNotIn("<b>x</b>", html)
        self.assertIn('<a href="https://example.com/a?b=1&amp;c=2">good</a>', html)

    def test_markdown_basics(self):
        out = build.markdown("one **bold** and *soft*\nsecond line\n\n- a\n- b\n\nlast `code`")
        self.assertIn("<strong>bold</strong>", out)
        self.assertIn("<em>soft</em>", out)
        self.assertIn("<br>second line", out)
        self.assertIn("<ul><li>a</li><li>b</li></ul>", out)
        self.assertIn("<code>code</code>", out)

    def test_projects_sorted_by_order_then_title(self):
        make({"content/site.json": {"name": "J"},
              "content/projects/b.json": {"title": "Zed", "order": 1},
              "content/projects/a.json": {"title": "Alpha", "order": 2},
              "content/projects/c.json": {"title": "Beta", "order": 2}})
        html, _ = build.render()
        self.assertLess(html.index("Zed"), html.index("Alpha"))
        self.assertLess(html.index("Alpha"), html.index("Beta"))

    def test_writing_newest_first_and_pagers_link_to_their_file(self):
        make({"content/site.json": {"name": "J"},
              "content/writing/old.json": {"title": "Old", "date": "2024-01-01", "url": "https://x.test/old"},
              "content/writing/new.json": {"title": "New", "date": "2026-05-01", "url": "https://x.test/new"},
              "content/pagers/p.json": {"title": "Pager", "file": "/pagers/p.pdf", "blurb": "About it"}})
        html, _ = build.render()
        self.assertLess(html.index("x.test/new"), html.index("x.test/old"))
        self.assertIn('<a href="/pagers/p.pdf">Pager</a>', html)

    def test_hidden_from_search_unless_made_public(self):
        make({"content/site.json": {"name": "J"}})
        html, public = build.render()
        self.assertIn('name="robots" content="noindex"', html)
        self.assertFalse(public)
        make({"content/site.json": {"name": "J", "public": True}})
        html, public = build.render()
        self.assertNotIn("noindex", html)
        self.assertTrue(public)

    def test_a_broken_content_file_does_not_stop_the_build(self):
        d = make({"content/site.json": {"name": "J"}})
        (d / "content/projects").mkdir(parents=True)
        (d / "content/projects/bad.json").write_text("{not json")
        (d / "content/projects/ok.json").write_text(json.dumps({"title": "Fine"}))
        html, _ = build.render()
        self.assertIn("Fine", html)

    def test_cms_config_points_at_real_content_files(self):
        cfg = (ROOT / "admin/config.yml").read_text()
        for f in ("content/site.json", "content/bb.json", "content/projects", "content/pagers", "content/writing"):
            self.assertIn(f, cfg)
            self.assertTrue((ROOT / f).exists(), f)


if __name__ == "__main__":
    unittest.main()
