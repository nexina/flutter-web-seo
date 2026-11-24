"""Command line: build | validate | indexnow."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import __version__, indexnow
from .config import ConfigError, load, output_file
from .render import render_shell
from .sitemap import build_robots, build_sitemap
from .validate import Issue, check_config, check_output


def _report(issues: list[Issue], strict: bool) -> bool:
    """Print issues; True when there is nothing that should fail the run."""
    for i in issues:
        print(i, file=sys.stderr)
    errors = [i for i in issues if i.level == "error" or strict]
    return not errors


def cmd_build(a: argparse.Namespace) -> int:
    cfg = load(a.config)
    template_path = Path(a.template)
    if not template_path.is_file():
        raise ConfigError(f"template not found: {template_path} (run `flutter build web` first)")
    out = Path(a.out) if a.out else template_path.parent
    if not a.no_validate and not _report(check_config(cfg), a.strict):
        print("build aborted: fix the problems above (or --no-validate)", file=sys.stderr)
        return 1

    template = template_path.read_text(encoding="utf-8")
    for route in cfg["routes"]:
        dest = output_file(out, route["path"])
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(render_shell(template, cfg["site"], route), encoding="utf-8")
    base = Path(a.config).resolve().parent
    (out / "sitemap.xml").write_text(
        build_sitemap(cfg, cwd=base, default_sources=[Path(a.config).name]), encoding="utf-8")
    (out / "robots.txt").write_text(build_robots(cfg), encoding="utf-8")
    key = cfg["site"].get("indexnow_key")
    if key:
        if not indexnow.valid_key(key):
            raise ConfigError("site.indexnow_key must be 8-128 chars of A-Z a-z 0-9 -")
        (out / f"{key}.txt").write_text(key, encoding="utf-8")
    print(f"wrote {len(cfg['routes'])} shells, sitemap.xml, robots.txt to {out}")
    if not a.no_validate and not _report(check_output(cfg, out), a.strict):
        return 1
    return 0


def cmd_validate(a: argparse.Namespace) -> int:
    cfg = load(a.config)
    issues = check_config(cfg)
    if a.out:
        issues += check_output(cfg, Path(a.out))
    ok = _report(issues, a.strict)
    n_err = sum(i.level == "error" for i in issues)
    print(f"{len(cfg['routes'])} routes, {n_err} errors, {len(issues) - n_err} warnings")
    return 0 if ok else 1


def cmd_indexnow(a: argparse.Namespace) -> int:
    cfg = load(a.config)
    site = cfg["site"]
    key = a.key or os.environ.get("INDEXNOW_KEY") or site.get("indexnow_key")
    if not indexnow.valid_key(key or ""):
        raise ConfigError("need an IndexNow key: --key, $INDEXNOW_KEY or site.indexnow_key (8-128 chars A-Za-z0-9-)")
    if a.sitemap:
        urls = indexnow.sitemap_urls(Path(a.sitemap).read_text(encoding="utf-8"))
    else:
        from .config import canonical
        from .sitemap import indexable
        urls = [canonical(site, r["path"]) for r in cfg["routes"] if indexable(r)]
    if not urls:
        raise ConfigError("no URLs to submit")
    batches = indexnow.payloads(site["url"], key, urls, a.key_location)
    for b in batches:
        if a.dry_run:
            print(f"[dry-run] POST {a.endpoint}: {len(b['urlList'])} URLs, host={b['host']}, keyLocation={b['keyLocation']}")
            continue
        status = indexnow.submit(b, a.endpoint)
        print(f"IndexNow {a.endpoint}: HTTP {status} for {len(b['urlList'])} URLs")
        if status not in (200, 202):
            print("warning: not 200/202 (is the key file live at keyLocation?)", file=sys.stderr)
            return 1
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="flutter-web-seo", description=__doc__)
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="write shells, sitemap.xml and robots.txt")
    b.add_argument("--config", "-c", default="routes.json")
    b.add_argument("--template", "-t", default="build/web/index.html", help="built Flutter index.html with SEO markers")
    b.add_argument("--out", "-o", help="output directory (default: the template's directory)")
    b.add_argument("--strict", action="store_true", help="treat warnings as errors")
    b.add_argument("--no-validate", action="store_true")
    b.set_defaults(fn=cmd_build)

    v = sub.add_parser("validate", help="check the config (and the built output with --out)")
    v.add_argument("--config", "-c", default="routes.json")
    v.add_argument("--out", "-o", help="also check a built output directory")
    v.add_argument("--strict", action="store_true")
    v.set_defaults(fn=cmd_validate)

    i = sub.add_parser("indexnow", help="submit URLs to IndexNow")
    i.add_argument("--config", "-c", default="routes.json")
    i.add_argument("--key")
    i.add_argument("--key-location", help="override https://<site>/<key>.txt")
    i.add_argument("--sitemap", help="read URLs from this sitemap.xml instead of the config")
    i.add_argument("--endpoint", default=indexnow.DEFAULT_ENDPOINT)
    i.add_argument("--dry-run", action="store_true")
    i.set_defaults(fn=cmd_indexnow)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.fn(args)
    except ConfigError as ex:
        print(f"error: {ex}", file=sys.stderr)
        return 2
