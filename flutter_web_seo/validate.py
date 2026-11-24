"""Validation: config-level rules and (optionally) the built output."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree

from . import markdown_lite as md
from .config import canonical, output_file

TITLE_MAX = 60
DESC_MIN, DESC_MAX = 120, 160
_PATH_OK = re.compile(r"^/[a-z0-9\-_/.]*$")


@dataclass
class Issue:
    level: str  # "error" | "warning"
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.level.upper():7} {self.where}: {self.message}"


def check_config(cfg: dict) -> list[Issue]:
    site, routes = cfg["site"], cfg["routes"]
    issues: list[Issue] = []
    err = lambda w, m: issues.append(Issue("error", w, m))  # noqa: E731
    warn = lambda w, m: issues.append(Issue("warning", w, m))  # noqa: E731

    u = urlparse(site["url"])
    if u.scheme != "https" or not u.netloc or u.path or u.query:
        err("site.url", 'must be an origin like "https://example.com" (https, no path)')
    if not site["name"]:
        warn("site.name", "empty; og:site_name and WebSite JSON-LD are skipped")
    if not site["default_og_image"] and not any(r.get("og_image") for r in routes):
        warn("site", "no og image anywhere; social previews will be text-only")

    paths: dict[str, str] = {}
    titles: dict[str, str] = {}
    descs: dict[str, str] = {}
    for r in routes:
        p = r["path"]
        if not _PATH_OK.match(p) or "//" in p or ".." in p:
            err(p, "path must be lower-case, start with '/', and have no '//', '..', query or fragment")
        if p != "/" and p.endswith("/"):
            err(p, "no trailing slash (the canonical form has none)")
        if p in paths:
            err(p, "duplicate path")
        paths[p] = p

        title, desc = (r.get("title") or "").strip(), (r.get("description") or "").strip()
        if not title:
            err(p, "missing title")
        elif len(title) > TITLE_MAX:
            err(p, f"title is {len(title)} chars (max {TITLE_MAX}): {title!r}")
        if not desc:
            err(p, "missing description")
        elif not DESC_MIN <= len(desc) <= DESC_MAX:
            err(p, f"description is {len(desc)} chars (want {DESC_MIN}-{DESC_MAX})")
        if title:
            if title.lower() in titles:
                err(p, f"title duplicates {titles[title.lower()]}")
            titles.setdefault(title.lower(), p)
        if desc:
            if desc.lower() in descs:
                err(p, f"description duplicates {descs[desc.lower()]}")
            descs.setdefault(desc.lower(), p)

        if not (r.get("h1") or title):
            err(p, "no h1")
        words = len(md.plain(r.get("body", "")).split())
        if not r.get("body_html") and words < 40 and not r.get("noindex"):
            warn(p, f"body has only {words} words; thin pages rarely rank")
        for b in r.get("breadcrumbs") or []:
            if not isinstance(b, dict) or not b.get("name") or not b.get("path"):
                err(p, 'each breadcrumb needs "name" and "path"')
        for f in r.get("faq") or []:
            if not f.get("q") or not f.get("a"):
                err(p, 'each faq entry needs "q" and "a"')
        if r.get("schema", "WebPage") not in ("WebApplication", "SoftwareApplication", "WebPage", "none"):
            err(p, f"unknown schema {r.get('schema')!r}")
        for it in r.get("items") or []:
            if not it.get("name") or not it.get("path"):
                err(p, 'each item needs "name" and "path"')

    known = set(paths)
    for r in routes:
        for b in r.get("breadcrumbs") or []:
            if isinstance(b, dict) and b.get("path") and b["path"] not in known:
                warn(r["path"], f"breadcrumb points at {b['path']}, which is not a route")
        for it in r.get("items") or []:
            if it.get("path") and it["path"] not in known:
                warn(r["path"], f"item points at {it['path']}, which is not a route")
    return issues


def check_sitemap(xml_text: str, site_url: str, out_dir: Path | None = None) -> list[Issue]:
    """Sitemap rules: absolute https on the site origin, no trailing slash
    (except the root), no query/fragment, lower case, unique, file exists."""
    issues: list[Issue] = []
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as ex:
        return [Issue("error", "sitemap.xml", f"not valid XML: {ex}")]
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    seen: set[str] = set()
    origin = urlparse(site_url)
    for el in root.findall("s:url", ns):
        loc = (el.findtext("s:loc", default="", namespaces=ns) or "").strip()
        bad = lambda m: issues.append(Issue("error", loc or "<empty loc>", m))  # noqa: E731
        u = urlparse(loc)
        if (u.scheme, u.netloc) != (origin.scheme, origin.netloc):
            bad(f"must be on {site_url}")
        if u.query or u.fragment:
            bad("no query string or fragment")
        if u.path != "/" and u.path.endswith("/"):
            bad("no trailing slash")
        if loc != loc.lower():
            bad("must be lower case")
        if loc in seen:
            bad("duplicate")
        seen.add(loc)
        lm = el.findtext("s:lastmod", default="", namespaces=ns)
        if lm and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", lm.strip()):
            bad(f"lastmod {lm!r} is not YYYY-MM-DD")
        if out_dir is not None and u.path is not None:
            if not output_file(out_dir, u.path or "/").is_file():
                bad("no shell file for this URL in the output directory")
    return issues


def check_output(cfg: dict, out_dir: Path) -> list[Issue]:
    """Re-read what was written: title/canonical/JSON-LD match, sitemap rules."""
    issues: list[Issue] = []
    site = cfg["site"]
    for r in cfg["routes"]:
        f = output_file(out_dir, r["path"])
        if not f.is_file():
            issues.append(Issue("error", r["path"], f"missing {f}"))
            continue
        text = f.read_text(encoding="utf-8")
        want = canonical(site, r["path"])
        if f'<link rel="canonical" href="{want}">' not in text:
            issues.append(Issue("error", r["path"], f"canonical is not {want}"))
        if text.count("<title>") != 1:
            issues.append(Issue("error", r["path"], f"expected exactly one <title>, found {text.count('<title>')}"))
        if 'id="seo-content"' not in text:
            issues.append(Issue("error", r["path"], "no #seo-content block"))
        for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', text, re.S):
            try:
                json.loads(m.group(1))
            except json.JSONDecodeError as ex:
                issues.append(Issue("error", r["path"], f"JSON-LD does not parse: {ex}"))
    sm = out_dir / "sitemap.xml"
    if sm.is_file():
        issues += check_sitemap(sm.read_text(encoding="utf-8"), site["url"], out_dir)
    else:
        issues.append(Issue("error", "sitemap.xml", "missing"))
    return issues
