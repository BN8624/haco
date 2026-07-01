# candidate_store: candidate 디렉터리 저장, hard filtering, rejected 격리.
import json

from haco.candidate_store import (apply_hard_filter, build_candidate_summary,
                                  write_patch_candidate, write_test_candidate)
from haco.run_store import create_run

_BASE = {"candidate_id": "candidate_01", "_target_files": ["pkg/calc.py"],
         "_language": "python", "preferred_apply_method": "search_replace",
         "summary": "s", "risk": "low", "reason": "x"}


def test_patch_candidate_real_search_replace(tmp_path):
    run = create_run(tmp_path)
    out = {**_BASE, "search_replace_edits": [
        {"file": "pkg/calc.py", "operation": "replace",
         "search": "def add(a, b): return a",
         "replace": "def add(a, b): return a + b", "notes": "fix"}]}
    write_patch_candidate(run, out)
    data = json.loads((run / "candidates" / "candidate_01" / "search_replace.json")
                      .read_text(encoding="utf-8"))
    assert data["edits"][0]["search"] == "def add(a, b): return a"
    assert data["edits"][0]["replace"] == "def add(a, b): return a + b"
    assert "<<<" not in json.dumps(data)  # placeholder 아님


def test_patch_candidate_real_replacement_blocks(tmp_path):
    run = create_run(tmp_path)
    out = {**_BASE, "preferred_apply_method": "full_block", "replacement_blocks": [
        {"file": "pkg/calc.py", "target": "add", "language": "python",
         "code": "def add(a, b):\n    return a + b",
         "apply_method": "replace entire function"}]}
    write_patch_candidate(run, out)
    md = (run / "candidates" / "candidate_01" / "replacement_blocks.md") \
        .read_text(encoding="utf-8")
    assert "def add(a, b):" in md
    assert "return a + b" in md
    assert "insert verified replacement here" not in md  # skeleton 아님


def test_patch_candidate_real_edit_plan(tmp_path):
    run = create_run(tmp_path)
    out = {**_BASE, "edit_plan": "1. open calc.py\n2. fix add()"}
    write_patch_candidate(run, out)
    md = (run / "candidates" / "candidate_01" / "edit_plan.md").read_text(encoding="utf-8")
    assert "1. open calc.py" in md
    assert "Notes for the main agent" not in md  # skeleton 헤더 아님


def test_patch_candidate_fallback_skeleton_when_empty(tmp_path):
    run = create_run(tmp_path)
    write_patch_candidate(run, dict(_BASE))
    sr = json.loads((run / "candidates" / "candidate_01" / "search_replace.json")
                    .read_text(encoding="utf-8"))
    assert "<<<" in sr["edits"][0]["search"]  # skeleton placeholder 유지
    md = (run / "candidates" / "candidate_01" / "edit_plan.md").read_text(encoding="utf-8")
    assert "Notes for the main agent" in md  # skeleton 유지


def test_write_patch_candidate_files(tmp_path):
    run = create_run(tmp_path)
    out = {"candidate_id": "candidate_01", "_target_files": ["pkg/calc.py"],
           "_language": "python", "preferred_apply_method": "search_replace",
           "summary": "add subtract", "risk": "low", "reason": "x"}
    meta = write_patch_candidate(run, out)
    cdir = run / "candidates" / "candidate_01"
    assert (cdir / "candidate.json").exists()
    assert (cdir / "edit_plan.md").exists()
    assert (cdir / "search_replace.json").exists()
    assert (cdir / "replacement_blocks.md").exists()
    assert meta.target_files == ["pkg/calc.py"]


def test_strategy_only_when_no_target(tmp_path):
    run = create_run(tmp_path)
    out = {"candidate_id": "candidate_01", "_target_files": [],
           "_language": "unknown", "preferred_apply_method": "strategy_only",
           "summary": "s", "risk": "low", "reason": "x"}
    meta = write_patch_candidate(run, out)
    assert meta.kind == "strategy"
    assert (run / "candidates" / "candidate_01" / "edit_plan.md").exists()


def test_hard_filter_rejects_and_moves(tmp_path):
    run = create_run(tmp_path)
    good = write_patch_candidate(run, {
        "candidate_id": "candidate_01", "_target_files": ["pkg/calc.py"],
        "_language": "python", "preferred_apply_method": "search_replace",
        "summary": "g", "risk": "low", "reason": "x",
        # 실제 anchor가 있어야 accepted 가능(placeholder skeleton은 masked).
        "search_replace_edits": [{"file": "pkg/calc.py", "operation": "replace",
                                  "search": "return a", "replace": "return a + b"}]})
    bad = write_patch_candidate(run, {
        "candidate_id": "candidate_02", "_target_files": [],
        "_language": "python", "preferred_apply_method": "full_block",
        "summary": "b", "risk": "high", "reason": "x"})
    snapshot = {"file_paths_sample": ["pkg/calc.py"], "repo_map": []}
    judge = {"accepted_candidates": ["candidate_01"], "rejected_candidates": [],
             "best_candidate": "candidate_01"}
    metas = apply_hard_filter(run, [good, bad], judge, snapshot)
    statuses = {m.candidate_id: m.judge_status for m in metas}
    assert statuses["candidate_01"] == "accepted"
    # candidate_02: target 없음 + strategy_only 아님 → rejected, rejected/로 이동
    assert statuses["candidate_02"] == "rejected"
    assert (run / "candidates" / "rejected" / "candidate_02").exists()
    assert not (run / "candidates" / "candidate_02").exists()


def test_accepted_not_in_brief_when_path_unknown(tmp_path):
    run = create_run(tmp_path)
    meta = write_patch_candidate(run, {
        "candidate_id": "candidate_01", "_target_files": ["ghost/missing.py"],
        "_language": "python", "preferred_apply_method": "search_replace",
        "summary": "g", "risk": "low", "reason": "x"})
    snapshot = {"file_paths_sample": ["pkg/calc.py"], "repo_map": []}
    judge = {"accepted_candidates": ["candidate_01"]}
    metas = apply_hard_filter(run, [meta], judge, snapshot)
    # snapshot에 없는 경로 → accepted에서 masked로 강등
    assert metas[0].judge_status == "masked"
    assert metas[0].expose_in_execution_brief is False


def test_summary_counts(tmp_path):
    run = create_run(tmp_path)
    p = write_patch_candidate(run, {"candidate_id": "candidate_01",
                                    "_target_files": ["pkg/calc.py"],
                                    "_language": "python",
                                    "preferred_apply_method": "search_replace",
                                    "summary": "s", "risk": "low", "reason": "x",
                                    "search_replace_edits": [
                                        {"file": "pkg/calc.py", "operation": "replace",
                                         "search": "return a", "replace": "return a+b"}]})
    t = write_test_candidate(run, {"_language": "python", "test_scope": "focused",
                                   "tests_to_run": ["pytest"], "reason": "x"},
                             "candidate_test_01")
    snapshot = {"file_paths_sample": ["pkg/calc.py"], "repo_map": []}
    judge = {"accepted_candidates": ["candidate_01", "candidate_test_01"],
             "best_candidate": "candidate_01"}
    metas = apply_hard_filter(run, [p, t], judge, snapshot)
    cs = build_candidate_summary(metas, judge)
    assert cs.generated == 2
    assert cs.accepted == 2
    assert "candidate_01" in cs.patch_candidates
    assert "candidate_test_01" in cs.test_candidates
