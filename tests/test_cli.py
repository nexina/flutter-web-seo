import json
import shutil
from pathlib import Path

from flutter_web_seo import indexnow
from flutter_web_seo.cli import main

ROOT = Path(__file__).resolve().parent.parent
CFG = str(ROOT / "examples" / "routes.json")


def test_build_end_to_end(tmp_path):
    out = tmp_path / "web"
    out.mkdir()
    shutil.copy(ROOT / "tests" / "fixtures" / "index.html", out / "index.html")
    assert main(["build", "-c", CFG, "-t", str(out / "index.html"), "--strict"]) == 0
    for p in ("index.html", "word-counter/index.html", "case-converter/index.html", "sitemap.xml", "robots.txt"):
        assert (out / p).is_file(), p
    assert main(["validate", "-c", CFG, "--out", str(out), "--strict"]) == 0
    # a second run on its own output is stable
    first = (out / "word-counter" / "index.html").read_text()
    assert main(["build", "-c", CFG, "-t", str(out / "index.html")]) == 0
    assert (out / "word-counter" / "index.html").read_text() == first


def test_build_aborts_on_bad_config(tmp_path):
    raw = json.loads(Path(CFG).read_text())
    raw["routes"][1]["title"] = "x" * 80
    cfg = tmp_path / "r.json"
    cfg.write_text(json.dumps(raw))
    shutil.copy(ROOT / "tests" / "fixtures" / "index.html", tmp_path / "index.html")
    assert main(["build", "-c", str(cfg), "-t", str(tmp_path / "index.html")]) == 1
    assert not (tmp_path / "sitemap.xml").exists()


def test_missing_template_and_config(tmp_path):
    assert main(["build", "-c", CFG, "-t", str(tmp_path / "nope.html")]) == 2
    assert main(["validate", "-c", str(tmp_path / "nope.json")]) == 2


def test_validate_detects_tampered_output(tmp_path):
    out = tmp_path / "web"
    out.mkdir()
    shutil.copy(ROOT / "tests" / "fixtures" / "index.html", out / "index.html")
    main(["build", "-c", CFG, "-t", str(out / "index.html")])
    (out / "case-converter" / "index.html").unlink()
    assert main(["validate", "-c", CFG, "--out", str(out)]) == 1


def test_indexnow_payload_and_dry_run(capsys):
    p = indexnow.payloads("https://example.com", "my-indexnow-key", ["https://example.com/a"])
    assert p == [{"host": "example.com", "key": "my-indexnow-key",
                  "keyLocation": "https://example.com/my-indexnow-key.txt",
                  "urlList": ["https://example.com/a"]}]
    assert len(indexnow.payloads("https://e.com", "my-indexnow-key", ["u"] * 25000)) == 3
    assert main(["indexnow", "-c", CFG, "--key", "my-indexnow-key", "--dry-run"]) == 0
    assert "3 URLs" in capsys.readouterr().out


def test_indexnow_rejects_bad_key():
    assert main(["indexnow", "-c", CFG, "--key", "short", "--dry-run"]) == 2


def test_indexnow_sitemap_urls():
    assert indexnow.sitemap_urls("<loc>https://a.com/x</loc>\n<loc> https://a.com/y </loc>") == [
        "https://a.com/x", "https://a.com/y"]
