"""sitemap.xml and robots.txt."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from .config import canonical
from .lastmod import route_lastmod


def indexable(route: dict) -> bool:
    return not route.get("noindex") and route.get("sitemap", True)


def build_sitemap(cfg: dict, cwd: str | Path = ".", default_sources: list[str] | None = None) -> str:
    site = cfg["site"]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for r in cfg["routes"]:
        if not indexable(r):
            continue
        lines.append("  <url>")
        lines.append(f"    <loc>{escape(canonical(site, r['path']))}</loc>")
        lm = route_lastmod(r, default_sources or [], cwd)
        if lm:
            lines.append(f"    <lastmod>{lm}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def build_robots(cfg: dict) -> str:
    site = cfg["site"]
    rb = site["robots"]
    out = ["User-agent: *", "Allow: /"]
    out += [f"Disallow: {p}" for p in rb.get("disallow", [])]
    out += list(rb.get("extra", []))
    out += ["", f"Sitemap: {site['url']}/sitemap.xml"]
    return "\n".join(out) + "\n"
