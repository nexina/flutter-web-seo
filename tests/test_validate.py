import copy

from flutter_web_seo.config import normalise
from flutter_web_seo.validate import check_config, check_sitemap


def errors(raw):
    return [str(i) for i in check_config(normalise(raw)) if i.level == "error"]


def test_example_is_clean(cfg):
    assert [i for i in check_config(cfg) if i.level == "error"] == []


def test_title_too_long(raw):
    raw["routes"][1]["title"] = "x" * 61
    assert any("title is 61" in e for e in errors(raw))


def test_description_range(raw):
    raw["routes"][1]["description"] = "short"
    assert any("description is 5" in e for e in errors(raw))
    raw["routes"][1]["description"] = "y" * 161
    assert any("description is 161" in e for e in errors(raw))


def test_duplicates(raw):
    raw["routes"][2]["title"] = raw["routes"][1]["title"].upper()
    raw["routes"][2]["description"] = raw["routes"][1]["description"]
    e = errors(raw)
    assert any("title duplicates" in x for x in e) and any("description duplicates" in x for x in e)


def test_bad_paths(raw):
    raw["routes"][1]["path"] = "/Word-Counter/"
    e = errors(raw)
    assert any("lower-case" in x for x in e) and any("trailing slash" in x for x in e)


def test_duplicate_path_and_bad_site_url(raw):
    raw["routes"][2]["path"] = "/word-counter"
    raw["site"]["url"] = "http://example.com/app"
    e = errors(raw)
    assert any("duplicate path" in x for x in e) and any("site.url" in x for x in e)


SM = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{}</urlset>'


def sm(*locs):
    return SM.format("".join(f"<url><loc>{l}</loc></url>" for l in locs))


def test_sitemap_rules():
    ok = check_sitemap(sm("https://example.com/", "https://example.com/a"), "https://example.com")
    assert ok == []
    bad = check_sitemap(sm("https://example.com/a/", "https://example.com/A", "https://example.com/b?x=1",
                          "https://other.com/c", "https://example.com/A"), "https://example.com")
    msgs = " | ".join(str(i) for i in bad)
    for needle in ("trailing slash", "lower case", "query", "must be on", "duplicate"):
        assert needle in msgs


def test_sitemap_files_exist(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "index.html").write_text("x")
    bad = check_sitemap(sm("https://example.com/a", "https://example.com/missing"), "https://example.com", tmp_path)
    assert len(bad) == 1 and "missing" in str(bad[0])
