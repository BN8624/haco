# repo_map: Python AST 추출, import, docstring, fallback.
from haco.repo_map import build_repo_map, extract_python_symbols


def test_extract_function_and_class():
    src = ('import os\nfrom sys import path\n\n'
           'def run(task: str) -> dict:\n    """Run one task and return result."""\n'
           '    return {}\n\nclass Worker:\n    def go(self):\n        pass\n')
    syms = extract_python_symbols(src)
    kinds = {s["kind"] for s in syms}
    assert "imports" in kinds
    assert any(s.get("name") == "run" and "task: str" in s.get("signature", "")
               for s in syms)
    fn = next(s for s in syms if s.get("name") == "run")
    assert "Run one task" in fn["docstring_preview"]
    cls = next(s for s in syms if s.get("name") == "Worker")
    assert "go" in cls["methods"]


def test_build_repo_map_status(sample_project):
    files = ["pkg/calc.py", "tests/test_calc.py"]
    repo_map, status, notes = build_repo_map(sample_project, files)
    assert status == "ok"
    assert any(item["file"] == "pkg/calc.py" for item in repo_map)


def test_parse_failure_fallback(sample_project):
    (sample_project / "broken.py").write_text("def (:\n", encoding="utf-8")
    repo_map, status, notes = build_repo_map(
        sample_project, ["broken.py", "pkg/calc.py"])
    assert status in ("partial", "ok")
    # 파싱 실패해도 전체가 죽지 않는다
    assert isinstance(repo_map, list)
