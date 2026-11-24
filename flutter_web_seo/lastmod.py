"""``<lastmod>`` from git history.

Search engines learn to ignore ``lastmod`` when it is "today" on every
deploy. So the date is the last commit that touched the files that feed the
page, never the build date. No git, no history, or no sources: no date.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def git_date(paths: list[str], cwd: str | Path = ".") -> str | None:
    """``YYYY-MM-DD`` of the newest commit touching any of ``paths``."""
    if not paths:
        return None
    try:
        res = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", *paths],
            cwd=str(cwd), capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    out = res.stdout.strip()
    return out if res.returncode == 0 and len(out) == 10 else None


def route_lastmod(route: dict, default_sources: list[str], cwd: str | Path) -> str | None:
    """Explicit ``lastmod`` wins; else git date of ``sources``; else of the defaults."""
    if route.get("lastmod"):
        return str(route["lastmod"])
    return git_date(route.get("sources") or default_sources, cwd)
