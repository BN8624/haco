# scanner: project_snapshot 생성, ignore_dirs, 언어/타입/프레임워크 감지.
from haco.scanner import _keyword_matches, scan_project


def test_keyword_matches_relevance_ranking():
    # 회귀: 구체적 키워드에 맞는 파일이 일반 키워드에만 맞는 파일보다 앞서야 한다.
    files = ["GODSEED_MASTER_PLAN.md", "verify_phase0.py", "verify_phase2f.py"]
    kws = ["GODSEED", "phase2f", "verify_phase2f"]
    out = _keyword_matches(kws, files)
    assert out[0] == "verify_phase2f.py"
    assert "GODSEED_MASTER_PLAN.md" in out
    assert out.index("verify_phase2f.py") < out.index("GODSEED_MASTER_PLAN.md")


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


def test_unknown_language(empty_project, config):
    snap = scan_project(empty_project, "task", config)
    assert snap["primary_language"] == "unknown"
    assert snap["project_type"] == "unknown"
