"""Turn one route + the built Flutter ``index.html`` into a static shell."""

from __future__ import annotations

import html
import json
import re

from . import markdown_lite as md
from .config import ConfigError, canonical

# Why clip-based hiding and not display:none / visibility:hidden / hidden:
# crawlers (and AI fetchers that render) treat content that is not rendered as
# content that is not there, and Google's guidance is that text hidden from
# *all* users may be ignored. A 1px clipped box is still "rendered", is read by
# screen readers, and is revealed in full when JS is off or Flutter fails.
VISUALLY_HIDDEN_CSS = (
    ".visually-hidden{position:absolute!important;width:1px;height:1px;margin:-1px;"
    "padding:0;overflow:hidden;clip:rect(0,0,0,0);clip-path:inset(50%);"
    "white-space:nowrap;border:0}"
)
NOSCRIPT_CSS = (
    "#seo-content.visually-hidden{position:static!important;width:auto;height:auto;"
    "margin:16px;overflow:visible;clip:auto;clip-path:none;white-space:normal}"
    "#boot-splash{display:none!important}"
)

_HEAD = re.compile(r"(<!--\s*SEO_HEAD_START\s*-->)(.*?)(<!--\s*SEO_HEAD_END\s*-->)", re.S)
_BODY = re.compile(r"(<!--\s*SEO_CONTENT_START\s*-->)(.*?)(<!--\s*SEO_CONTENT_END\s*-->)", re.S)
_BOOT = re.compile(r"(<p\b[^>]*\bid=[\"']boot-title[\"'][^>]*>)(.*?)(</p>)", re.S)
_STRIP = [
    re.compile(r"<title\b[^>]*>.*?</title>\s*", re.S | re.I),
    re.compile(r"<meta\s+name=[\"'](?:description|robots)[\"'][^>]*>\s*", re.I),
    re.compile(r"<link\s+rel=[\"']canonical[\"'][^>]*>\s*", re.I),
    re.compile(r"<meta\s+(?:property|name)=[\"'](?:og|twitter):[^>]*>\s*", re.I),
]


def e(s: object) -> str:
    return html.escape(str(s), quote=True)


def ld(obj: dict) -> str:
    """One JSON-LD block. ``<`` is escaped so text can never close the tag."""
    data = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return f'<script type="application/ld+json">{data}</script>'


def breadcrumb_trail(site: dict, route: dict) -> list[tuple[str, str]]:
    """``[(name, path), ...]`` Home -> ancestors -> current page. [] for none."""
    if route["path"] == "/" or route.get("breadcrumbs") is False:
        return []
    trail = [(site["home_breadcrumb"], "/")]
    for b in route.get("breadcrumbs") or []:
        trail.append((b["name"], b["path"]))
    trail.append((route.get("breadcrumb_name") or route.get("h1") or route["title"], route["path"]))
    return trail


def jsonld_blocks(site: dict, route: dict) -> list[dict]:
    url = canonical(site, route["path"])
    desc = route.get("description", "")
    kind = route.get("schema", "WebPage")
    blocks: list[dict] = []

    if kind in ("WebApplication", "SoftwareApplication"):
        app = {
            "@context": "https://schema.org", "@type": kind,
            "name": route.get("name") or route.get("h1") or route["title"],
            "url": url, "description": desc,
            "applicationCategory": route.get("application_category") or site["application_category"],
            "operatingSystem": site["operating_system"],
        }
        offer = route.get("offer", site.get("offer"))
        if offer:
            app["offers"] = {"@type": "Offer", "price": str(offer["price"]),
                             "priceCurrency": offer["currency"]}
        blocks.append(app)
    elif kind == "WebPage":
        page = {"@context": "https://schema.org", "@type": "WebPage",
                "name": route["title"], "url": url, "description": desc}
        if site.get("name"):
            page["isPartOf"] = {"@type": "WebSite", "name": site["name"], "url": site["url"] + "/"}
        blocks.append(page)
    elif kind != "none":
        raise ConfigError(f'{route["path"]}: unknown schema {kind!r}')

    trail = breadcrumb_trail(site, route)
    if trail:
        blocks.append({
            "@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": i, "name": n, "item": canonical(site, p)}
                for i, (n, p) in enumerate(trail, 1)],
        })
    if route.get("faq"):
        blocks.append({
            "@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": md.plain(f["q"]),
                 "acceptedAnswer": {"@type": "Answer", "text": md.plain(f["a"])}}
                for f in route["faq"]],
        })
    if route.get("items"):
        blocks.append({
            "@context": "https://schema.org", "@type": "ItemList",
            "itemListElement": [
                {"@type": "ListItem", "position": i, "name": it["name"],
                 "url": canonical(site, it["path"])}
                for i, it in enumerate(route["items"], 1)],
        })
    return blocks


def head_html(site: dict, route: dict) -> str:
    url = canonical(site, route["path"])
    title, desc = route["title"], route.get("description", "")
    img = route.get("og_image") or site.get("default_og_image") or ""
    if img.startswith("/"):
        img = site["url"] + img
    lines = [
        f"<title>{e(title)}</title>",
        f'<meta name="description" content="{e(desc)}">',
        f'<link rel="canonical" href="{e(url)}">',
    ]
    if route.get("noindex"):
        lines.append('<meta name="robots" content="noindex,follow">')
    og = [("og:type", "website"), ("og:site_name", site.get("name", "")),
          ("og:title", title), ("og:description", desc), ("og:url", url),
          ("og:locale", site.get("locale", ""))]
    if img:
        og.append(("og:image", img))
    lines += [f'<meta property="{k}" content="{e(v)}">' for k, v in og if v]
    tw = [("twitter:card", "summary_large_image" if img else "summary"),
          ("twitter:title", title), ("twitter:description", desc),
          ("twitter:site", site.get("twitter_site", ""))]
    if img:
        tw.append(("twitter:image", img))
    lines += [f'<meta name="{k}" content="{e(v)}">' for k, v in tw if v]
    lines += [ld(b) for b in jsonld_blocks(site, route)]
    lines.append(f"<style>{VISUALLY_HIDDEN_CSS}</style>")
    lines.append(f"<noscript><style>{NOSCRIPT_CSS}</style></noscript>")
    return "\n".join(lines)


def content_html(site: dict, route: dict) -> str:
    parts = ['<div id="seo-content" class="visually-hidden">']
    parts.append("<noscript><p>This app needs JavaScript. The page content is below.</p></noscript>")
    trail = breadcrumb_trail(site, route)
    if trail:
        lis = [f'<li><a href="{e(p)}">{e(n)}</a></li>' for n, p in trail[:-1]]
        lis.append(f'<li aria-current="page">{e(trail[-1][0])}</li>')
        parts.append(f'<nav aria-label="Breadcrumb"><ol>{"".join(lis)}</ol></nav>')
    parts.append(f'<h1>{e(route.get("h1") or route["title"])}</h1>')
    if route.get("body_html"):
        parts.append(route["body_html"])  # trusted: written by the site author
    elif route.get("body"):
        parts.append(md.render(route["body"]))
    if route.get("items"):
        lis = "".join(
            f'<li><a href="{e(i["path"])}">{e(i["name"])}</a>'
            + (f' - {e(i["description"])}' if i.get("description") else "") + "</li>"
            for i in route["items"])
        parts.append(f'<h2>{e(site["related_heading"])}</h2><ul>{lis}</ul>')
    if route.get("faq"):
        parts.append(f'<h2>{e(site["faq_heading"])}</h2>')
        for f in route["faq"]:
            parts.append(f'<h3>{e(md.plain(f["q"]))}</h3>\n{md.render(f["a"])}')
    parts.append("</div>")
    return "\n".join(parts)


def check_template(template: str) -> list[str]:
    missing = []
    if not _HEAD.search(template):
        missing.append("<!-- SEO_HEAD_START --> ... <!-- SEO_HEAD_END -->")
    if not _BODY.search(template):
        missing.append("<!-- SEO_CONTENT_START --> ... <!-- SEO_CONTENT_END -->")
    return missing


def render_shell(template: str, site: dict, route: dict) -> str:
    missing = check_template(template)
    if missing:
        raise ConfigError("template is missing marker comments: " + "; ".join(missing))
    head, body = head_html(site, route), content_html(site, route)
    # Mask the marker regions so the strip below only touches the template's
    # own default <title>/<meta>/<link> (Flutter ships a generic set).
    tpl = _HEAD.sub("\x01HEAD\x01", template, count=1)
    tpl = _BODY.sub("\x01BODY\x01", tpl, count=1)
    for rx in _STRIP:
        tpl = rx.sub("", tpl)
    boot = route.get("boot_title") or route.get("h1") or route["title"]
    tpl = _BOOT.sub(lambda m: m.group(1) + e(boot) + m.group(3), tpl, count=1)
    tpl = tpl.replace("\x01HEAD\x01", f"<!-- SEO_HEAD_START -->\n{head}\n<!-- SEO_HEAD_END -->")
    tpl = tpl.replace("\x01BODY\x01", f"<!-- SEO_CONTENT_START -->\n{body}\n<!-- SEO_CONTENT_END -->")
    return tpl
