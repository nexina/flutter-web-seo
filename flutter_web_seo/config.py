"""Loading and normalising the routes config (plain JSON)."""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_SITE = {
    "name": "",
    "url": "",
    "locale": "en_US",
    "default_og_image": "",
    "twitter_site": "",
    "application_category": "UtilitiesApplication",
    "operating_system": "Web",
    "offer": {"price": "0", "currency": "USD"},
    "faq_heading": "Frequently asked questions",
    "related_heading": "Related",
    "home_breadcrumb": "Home",
    "indexnow_key": "",
    "robots": {"disallow": [], "extra": []},
}


class ConfigError(Exception):
    """Raised for an unreadable or structurally broken config."""


def load(path: str | Path) -> dict:
    p = Path(path)
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"config not found: {p}")
    except json.JSONDecodeError as e:
        raise ConfigError(f"{p}: invalid JSON: {e}")
    return normalise(raw)


def normalise(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise ConfigError("config must be a JSON object")
    site = {**DEFAULT_SITE, **(raw.get("site") or {})}
    site["robots"] = {**DEFAULT_SITE["robots"], **(site.get("robots") or {})}
    site["url"] = str(site["url"]).rstrip("/")
    routes = raw.get("routes")
    if not isinstance(routes, list) or not routes:
        raise ConfigError('config needs a non-empty "routes" list')
    out = []
    for i, r in enumerate(routes):
        if not isinstance(r, dict) or not isinstance(r.get("path"), str):
            raise ConfigError(f"routes[{i}] needs a string \"path\"")
        out.append(r)
    return {"site": site, "routes": out}


def canonical(site: dict, path: str) -> str:
    """Absolute canonical URL. No trailing slash; the root keeps its one."""
    return site["url"] + ("/" if path == "/" else path)


def output_file(out_dir: Path, path: str) -> Path:
    """Where a route's shell lives. Refuses paths that escape ``out_dir``."""
    rel = path.strip("/")
    target = (out_dir / rel / "index.html") if rel else (out_dir / "index.html")
    if ".." in Path(rel).parts:
        raise ConfigError(f"unsafe route path: {path!r}")
    return target
