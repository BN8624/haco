# pytest 공용 픽스처: 샘플 프로젝트와 config.
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from haco.config import load_config  # noqa: E402


@pytest.fixture
def config():
    return load_config()


@pytest.fixture
def sample_project(tmp_path):
    proj = tmp_path / "proj"
    (proj / "pkg").mkdir(parents=True)
    (proj / "tests").mkdir(parents=True)
    (proj / "pyproject.toml").write_text(
        '[project]\nname = "sample"\n\n[tool.pytest.ini_options]\ntestpaths=["tests"]\n',
        encoding="utf-8")
    (proj / "pkg" / "calc.py").write_text(
        'def add(a, b):\n    """Add two numbers."""\n    return a + b\n\n'
        'class Calculator:\n    def multiply(self, a, b):\n        return a * b\n',
        encoding="utf-8")
    (proj / "tests" / "test_calc.py").write_text(
        "from pkg.calc import add\n\ndef test_add():\n    assert add(1, 2) == 3\n",
        encoding="utf-8")
    (proj / "README.md").write_text("# Sample\n", encoding="utf-8")
    return proj


@pytest.fixture
def empty_project(tmp_path):
    proj = tmp_path / "empty"
    proj.mkdir()
    return proj
