# scanner: project_snapshot 생성, ignore_dirs, 언어/타입/프레임워크 감지.
import shutil
import subprocess

import pytest

from haco.scanner import _extract_keywords, _keyword_matches, scan_project


def test_extract_keywords_korean_mixed():
    # 한국어 작업 지시 + 혼합 토큰이 모두 추출돼야 한다.
    kws = _extract_keywords("갓시드 phase2f ticks10000 검증 결과 문서 갱신")
    for expected in ["갓시드", "phase2f", "ticks10000", "검증", "결과", "문서", "갱신"]:
        assert expected in kws


def test_extract_keywords_preserves_english_and_filters_noise():
    # 영어 식별자 추출 동작 보존 + stopword/짧은 잡음 필터.
    kws = _extract_keywords("update verify_phase2f and config loader to 10k")
    assert "verify_phase2f" in kws
    assert "config" in kws
    assert "loader" in kws
    assert "10k" in kws          # 숫자 혼합 유지
    assert "and" not in kws      # stopword
    assert "to" not in kws       # 2자 순수 영문 잡음


def test_extract_keywords_identifiers_first():
    # Intent Expansion: 코드 식별자가 일반 산문어보다 앞서야 locator [:8] 절단에서 살아남는다.
    kws = _extract_keywords(
        "refactor the loader helper compute_starvation_pressure update_population")
    assert "compute_starvation_pressure" in kws
    assert "update_population" in kws
    assert kws.index("compute_starvation_pressure") < kws.index("loader")
    assert kws.index("update_population") < kws.index("helper")


def test_keyword_matches_filename_stem_boost():
    # task가 명시한 파일 stem 정확매칭이 같은 접두 substring보다 확실히 앞선다(phase5 vs phase3).
    files = ["verify_phase3a.py", "verify_phase3b.py", "verify_phase5a.py"]
    out = _keyword_matches(["verify_phase5a", "phase"], files)
    assert out[0] == "verify_phase5a.py"


def test_keyword_matches_content_aware():
    # 파일명이 안 맞아도 그 파일의 repo_map 심볼이 키워드와 맞으면 상위로 온다.
    files = ["phase0_engine.py", "utils.py"]
    repo_map = [
        {"file": "phase0_engine.py", "symbols": [
            {"kind": "function", "name": "compute_starvation_pressure"}]},
        {"file": "utils.py", "symbols": [{"kind": "function", "name": "helper"}]},
    ]
    out = _keyword_matches(["compute_starvation_pressure"], files, repo_map)
    assert out and out[0] == "phase0_engine.py"  # 파일명엔 없지만 심볼로 잡힘


def test_keyword_matches_relevance_ranking():
    # 회귀: 구체적 키워드에 맞는 파일이 일반 키워드에만 맞는 파일보다 앞서야 한다.
    files = ["GODSEED_MASTER_PLAN.md", "verify_phase0.py", "verify_phase2f.py"]
    kws = ["GODSEED", "phase2f", "verify_phase2f"]
    out = _keyword_matches(kws, files)
    assert out[0] == "verify_phase2f.py"
    assert "GODSEED_MASTER_PLAN.md" in out
    assert out.index("verify_phase2f.py") < out.index("GODSEED_MASTER_PLAN.md")


def test_keyword_matches_downranks_archive():
    # 회귀: 닫힌/과거 문서(docs/archive/...)는 동일 키워드를 맞춰도 live 파일보다 뒤로 밀린다.
    files = ["docs/archive/phase4/PHASE_4_IMPLEMENTATION_PLAN.md",
             "verify_phase5a.py", "phase0_engine.py"]
    kws = ["phase", "verify_phase5a"]
    out = _keyword_matches(kws, files)
    assert out[0] == "verify_phase5a.py"
    # archive 문서는 목록엔 남되 live 파일보다 뒤.
    arch = "docs/archive/phase4/PHASE_4_IMPLEMENTATION_PLAN.md"
    assert out.index("verify_phase5a.py") < out.index(arch)


def test_snapshot_basic_fields(sample_project, config):
    snap = scan_project(sample_project, "add subtract", config)
    assert snap["primary_language"] == "python"
    assert snap["project_type"] == "python_package"
    assert "pytest" in snap["test_frameworks"]
    assert "repo_map" in snap
    assert snap["repo_map_status"] in ("ok", "partial", "skipped")


def test_ignore_dirs_applied(sample_project, config):
    (sample_project / "node_modules").mkdir()
    (sample_project / "node_modules" / "junk.py").write_text("x=1", encoding="utf-8")
    snap = scan_project(sample_project, "task", config)
    assert all("node_modules" not in p for p in snap["file_paths_sample"])


def test_important_files_detected(sample_project, config):
    snap = scan_project(sample_project, "task", config)
    names = [p.split("/")[-1] for p in snap["important_files"]]
    assert "pyproject.toml" in names
    assert "README.md" in names


def test_keyword_matches(sample_project, config):
    snap = scan_project(sample_project, "modify calc module", config)
    assert any("calc" in p for p in snap["keyword_file_matches"])


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_scan_respects_gitignore(tmp_path, config):
    # git이 무시하는 root scratch 산출물은 file_paths_sample/keyword_matches에서 제외돼야 한다.
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / ".gitignore").write_text("/phase_scratch_*.json\n", encoding="utf-8")
    (tmp_path / "engine.py").write_text("# real source\nx = 1\n", encoding="utf-8")
    (tmp_path / "phase_scratch_summary.json").write_text("{}", encoding="utf-8")
    snap = scan_project(tmp_path, "edit engine marker", config)
    paths = snap["file_paths_sample"]
    assert "engine.py" in paths
    assert "phase_scratch_summary.json" not in paths


def test_unknown_language(empty_project, config):
    snap = scan_project(empty_project, "task", config)
    assert snap["primary_language"] == "unknown"
    assert snap["project_type"] == "unknown"
