"""A deliberately tiny Markdown subset, so the package needs no dependencies.

Supported blocks: paragraphs, ``##``..``####`` headings, ``-``/``*`` lists,
``1.`` lists. Supported inline: ``**bold**``, ``*italic*``, `` `code` ``,
``[text](url)``. Everything is HTML-escaped first, so the output is safe to
embed. Link targets must be http(s), mailto, ``/path`` or ``#anchor``;
anything else is rendered as plain text.
"""

from __future__ import annotations

import html
import re

_CODE = re.compile(r"`([^`]+)`")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])")
_HEADING = re.compile(r"^(#{2,4})\s+(.*\S)\s*$")
_UL = re.compile(r"^\s*[-*]\s+(.*)$")
_OL = re.compile(r"^\s*\d+[.)]\s+(.*)$")
_SAFE_URL = re.compile(r"^(https?://|mailto:|/|#)", re.I)


def inline(text: str) -> str:
    out = html.escape(text, quote=False)
    stash: list[str] = []

    def keep_code(m: re.Match) -> str:
        stash.append(m.group(1))
        return f"\x00{len(stash) - 1}\x00"

    out = _CODE.sub(keep_code, out)

    def link(m: re.Match) -> str:
        label, url = m.group(1), m.group(2)
        if not _SAFE_URL.match(html.unescape(url)):
            return label
        return f'<a href="{url.replace(chr(34), "%22")}">{label}</a>'

    out = _LINK.sub(link, out)
    out = _BOLD.sub(r"<strong>\1</strong>", out)
    out = _ITALIC.sub(r"<em>\1</em>", out)
    return re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{stash[int(m.group(1))]}</code>", out)


def render(text: str) -> str:
    """Markdown-lite -> HTML."""
    blocks: list[str] = []
    para: list[str] = []
    items: list[str] = []
    list_tag = ""

    def flush_para() -> None:
        if para:
            blocks.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()

    def flush_list() -> None:
        nonlocal list_tag
        if items:
            lis = "".join(f"<li>{inline(i)}</li>" for i in items)
            blocks.append(f"<{list_tag}>{lis}</{list_tag}>")
            items.clear()
        list_tag = ""

    for raw in (text or "").splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush_para()
            flush_list()
            continue
        h = _HEADING.match(line)
        ul = _UL.match(line)
        ol = _OL.match(line)
        if h:
            flush_para()
            flush_list()
            n = len(h.group(1))
            blocks.append(f"<h{n}>{inline(h.group(2))}</h{n}>")
        elif ul or ol:
            flush_para()
            tag = "ul" if ul else "ol"
            if list_tag and list_tag != tag:
                flush_list()
            list_tag = tag
            items.append((ul or ol).group(1))
        else:
            flush_list()
            para.append(line.strip())
    flush_para()
    flush_list()
    return "\n".join(blocks)


def plain(text: str) -> str:
    """Markdown-lite -> plain text (for JSON-LD and word counts)."""
    t = _LINK.sub(r"\1", text or "")
    t = _CODE.sub(r"\1", t)
    t = _BOLD.sub(r"\1", t)
    t = re.sub(r"(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])", r"\1", t)
    t = re.sub(r"(?m)^\s*(#{2,4}\s+|[-*]\s+|\d+[.)]\s+)", "", t)
    return re.sub(r"\s+", " ", t).strip()
