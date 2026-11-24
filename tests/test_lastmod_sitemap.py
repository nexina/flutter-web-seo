import subprocess

from flutter_web_seo.lastmod import git_date
from flutter_web_seo.sitemap import build_robots, build_sitemap


def git(cwd, *a):
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)


def test_git_date(tmp_path):
    git(tmp_path, "init", "-q")
    (tmp_path / "a.txt").write_text("1")
    git(tmp_path, "add", ".")
    env = {"GIT_COMMITTER_DATE": "2024-03-05T12:00:00", "GIT_AUTHOR_DATE": "2024-03-05T12:00:00"}
    import os
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"],
                   cwd=tmp_path, check=True, env={**os.environ, **env})
    assert git_date(["a.txt"], tmp_path) == "2024-03-05"
    assert git_date(["nope.txt"], tmp_path) is None
    assert git_date([], tmp_path) is None


def test_git_date_outside_repo(tmp_path):
    assert git_date(["x"], tmp_path) is None


def test_sitemap_skips_noindex_and_uses_explicit_lastmod(cfg, tmp_path):
    cfg["routes"][1]["noindex"] = True
    cfg["routes"][2]["lastmod"] = "2025-01-02"
    xml = build_sitemap(cfg, cwd=tmp_path)
    assert "word-counter" not in xml
    assert "<lastmod>2025-01-02</lastmod>" in xml
    assert "<loc>https://example.com/</loc>" in xml


def test_robots(cfg):
    cfg["site"]["robots"]["disallow"] = ["/private"]
    r = build_robots(cfg)
    assert "Disallow: /private" in r and r.strip().endswith("Sitemap: https://example.com/sitemap.xml")
