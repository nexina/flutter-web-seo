import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from flutter_web_seo.config import normalise  # noqa: E402

TEMPLATE = ROOT / "tests" / "fixtures" / "index.html"
EXAMPLE = ROOT / "examples" / "routes.json"


@pytest.fixture
def raw():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


@pytest.fixture
def cfg(raw):
    return normalise(copy.deepcopy(raw))


@pytest.fixture
def template():
    return TEMPLATE.read_text(encoding="utf-8")
