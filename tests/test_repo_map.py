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
    # §11: 심볼은 line 범위를 가져야 한다(context_pack excerpt의 전제).
    assert fn["line_start"] >= 1 and fn["line_end"] >= fn["line_start"]
    cls = next(s for s in syms if s.get("name") == "Worker")
    assert "go" in cls["methods"]
    assert cls["line_start"] >= 1 and cls["line_end"] >= cls["line_start"]


def test_extract_top_level_constants():
    # §5 2차 보강: top-level 상수/설정 테이블(UPPER_CASE, *_RELIEF/_YEARS 류)을 추출한다.
    src = ("LINEAGE_STARVATION_RELIEF = 0.25\n"
           "RELIEF_YEARS: int = 5\n"
           "helper = compute()\n"
           "def foo():\n    pass\n")
    syms = extract_python_symbols(src)
    consts = [s for s in syms if s["kind"] == "constant"]
    names = {s["name"] for s in consts}
    assert "LINEAGE_STARVATION_RELIEF" in names
    assert "RELIEF_YEARS" in names       # 타입 주석(AnnAssign)도 지원
    assert "helper" not in names         # 소문자 비상수는 제외
    c = next(s for s in consts if s["name"] == "LINEAGE_STARVATION_RELIEF")
    assert c["line_start"] == 1 and c["line_end"] >= 1


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
