# candidate_store: candidate 디렉터리 저장, hard filtering, rejected 격리.
from haco.candidate_store import (apply_hard_filter, build_candidate_summary,
                                  write_patch_candidate, write_test_candidate)
from haco.run_store import create_run


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
        "summary": "g", "risk": "low", "reason": "x"})
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
                                    "summary": "s", "risk": "low", "reason": "x"})
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
