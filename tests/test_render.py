import json
import re

import pytest

from flutter_web_seo.config import ConfigError
from flutter_web_seo.render import render_shell


def shell(cfg, template, path):
    route = next(r for r in cfg["routes"] if r["path"] == path)
    return render_shell(template, cfg["site"], route)


def ldjson(html):
    return [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]


def test_head_basics(cfg, template):
    out = shell(cfg, template, "/word-counter")
    assert out.count("<title>") == 1 and "<title>Demo app</title>" not in out
    assert '<link rel="canonical" href="https://example.com/word-counter">' in out
    assert 'property="og:image" content="https://example.com/og/default.png"' in out
    assert 'name="twitter:card" content="summary_large_image"' in out


def test_root_canonical_keeps_slash(cfg, template):
    assert '<link rel="canonical" href="https://example.com/">' in shell(cfg, template, "/")


def test_jsonld_types(cfg, template):
    types = [b["@type"] for b in ldjson(shell(cfg, template, "/word-counter"))]
    assert types == ["WebApplication", "BreadcrumbList", "FAQPage"]
    home = ldjson(shell(cfg, template, "/"))
    assert [b["@type"] for b in home] == ["WebPage", "ItemList"]
    crumbs = ldjson(shell(cfg, template, "/word-counter"))[1]["itemListElement"]
    assert [c["position"] for c in crumbs] == [1, 2]
    assert crumbs[-1]["item"] == "https://example.com/word-counter"


def test_content_is_visually_hidden_not_display_none(cfg, template):
    out = shell(cfg, template, "/word-counter")
    assert 'id="seo-content" class="visually-hidden"' in out
    assert "#seo-content{display:none" not in out and "visibility:hidden" not in out
    assert "#seo-content.visually-hidden{position:static" in out  # revealed without JS
    assert "<h1>Word counter</h1>" in out
    assert "<noscript>" in out


def test_boot_title(cfg, template):
    assert '<p id="boot-title">Word counter</p>' in shell(cfg, template, "/word-counter")


def test_idempotent(cfg, template):
    once = shell(cfg, template, "/word-counter")
    assert render_shell(once, cfg["site"], next(r for r in cfg["routes"] if r["path"] == "/word-counter")) == once


def test_escaping(cfg, template):
    r = {"path": "/x", "title": 'A "quoted" <b>', "description": "d", "h1": "<i>h</i>",
         "faq": [{"q": "q</script>", "a": "a"}]}
    out = render_shell(template, cfg["site"], r)
    assert "<b>" not in out and "<i>h</i>" not in out
    assert "q</script>" not in out            # '<' is escaped inside JSON-LD
    faq = [b for b in ldjson(out) if b["@type"] == "FAQPage"][0]
    assert faq["mainEntity"][0]["name"] == "q</script>"  # and round-trips intact


def test_noindex_route(cfg, template):
    r = {**cfg["routes"][1], "noindex": True}
    assert '<meta name="robots" content="noindex,follow">' in render_shell(template, cfg["site"], r)


def test_missing_markers(cfg):
    with pytest.raises(ConfigError, match="marker"):
        render_shell("<html><head></head><body></body></html>", cfg["site"], cfg["routes"][0])


def test_unknown_schema(cfg, template):
    with pytest.raises(ConfigError):
        render_shell(template, cfg["site"], {**cfg["routes"][1], "schema": "Nope"})


def test_breadcrumbs_ancestors_and_off(cfg, template):
    r = {**cfg["routes"][1], "breadcrumbs": [{"name": "Tools", "path": "/tools"}]}
    out = render_shell(template, cfg["site"], r)
    assert '<li><a href="/tools">Tools</a></li>' in out
    off = render_shell(template, cfg["site"], {**cfg["routes"][1], "breadcrumbs": False})
    assert "BreadcrumbList" not in off and 'aria-label="Breadcrumb"' not in off
