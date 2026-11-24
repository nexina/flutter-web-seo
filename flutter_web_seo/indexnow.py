"""IndexNow submission (https://www.indexnow.org/documentation)."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from urllib.parse import urlparse

DEFAULT_ENDPOINT = "https://api.indexnow.org/indexnow"
BATCH = 10000  # protocol maximum per request
_KEY = re.compile(r"^[A-Za-z0-9\-]{8,128}$")


def valid_key(key: str) -> bool:
    return bool(_KEY.match(key or ""))


def sitemap_urls(xml_text: str) -> list[str]:
    return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml_text)


def payloads(site_url: str, key: str, urls: list[str], key_location: str | None = None) -> list[dict]:
    host = urlparse(site_url).netloc
    loc = key_location or f"{site_url.rstrip('/')}/{key}.txt"
    return [
        {"host": host, "key": key, "keyLocation": loc, "urlList": urls[i:i + BATCH]}
        for i in range(0, len(urls), BATCH)
    ]


def submit(payload: dict, endpoint: str = DEFAULT_ENDPOINT, timeout: int = 30) -> int:
    """POST one batch; returns the HTTP status (200/202 = accepted)."""
    req = urllib.request.Request(
        endpoint, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json; charset=utf-8",
                 "User-Agent": "flutter-web-seo"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as ex:
        return ex.code
