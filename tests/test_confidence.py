# confidence: 결정론 fail-closed 판정기 + anchor 검증 + preflight 통합(§17.1).
from pathlib import Path

from haco.candidate_store import apply_hard_filter, write_patch_candidate
from haco.confidence import evaluate_confidence
from haco.model_client import MockProvider
from haco.preflight import run_preflight
from haco.run_store import create_run


def _snap(files):
    return {"file_paths_sample": files,
            "repo_map": [{"file": f, "symbols": [
                {"kind": "function", "name": "f", "line_start": 1, "line_end": 3}]}
                for f in files],
            "keyword_file_matches": files}


def _cp(nfiles, tokens=100):
    return {"files": [{} for _ in range(nfiles)],
            "budget": {"token_estimate": tokens, "max_tokens": 8000}}


def test_unknown_task_type_fails_closed(config):
    d = evaluate_confidence(snapshot=_snap(["a.py"]), locator={"files_to_read": ["a.py"]},
                            context_pack_json=_cp(1), task_type="unknown", config=config)
    assert d["fail_closed_triggered"] is True
    assert "task_intent_unclassified" in d["hard_gates_triggered"]


def test_too_many_files_fails_closed(config):
    files = [f"f{i}.py" for i in range(6)]  # > MAX_FILES_MEDIUM(5)
    d = evaluate_confidence(snapshot=_snap(files),
                            locator={"files_to_read": files},
                            context_pack_json=_cp(6), task_type="code_change",
                            config=config)
    assert d["fail_closed_triggered"] is True
    assert "too_many_files" in d["hard_gates_triggered"]


def test_no_range_fails_closed(config):
    # 파일은 있는데 focused range를 못 좁힘 → fail closed.
    d = evaluate_confidence(snapshot=_snap(["a.py"]), locator={"files_to_read": ["a.py"]},
                            context_pack_json=_cp(0), task_type="code_change",
                            config=config)
    assert d["fail_closed_triggered"] is True
    assert "no_symbol_section_or_range" in d["hard_gates_triggered"]


def test_no_deterministic_evidence_fails_closed(config):
    # 파일 후보는 있으나 snapshot/repo_map 어디에도 없고 range도 없음 → 신호 0.
    d = evaluate_confidence(snapshot={}, locator={"files_to_read": ["ghost.py"]},
                            context_pack_json=_cp(0), task_type="code_change",
                            config=config)
    assert d["fail_closed_triggered"] is True
    assert d["deterministic_signal_count"] == 0


def test_good_evidence_is_high(config):
    d = evaluate_confidence(snapshot=_snap(["a.py"]), locator={"files_to_read": ["a.py"]},
                            context_pack_json=_cp(1), task_type="code_change",
                            config=config)
    assert d["fail_closed_triggered"] is False
    assert d["confidence_tier"] == "high"
    assert d["deterministic_signal_count"] >= 2


def test_anchor_placeholder_not_accepted(tmp_path):
    run = create_run(tmp_path)
    # search_replace_edits 없음 → candidate_store가 placeholder skeleton 생성.
    meta = write_patch_candidate(run, {
        "candidate_id": "candidate_01", "_target_files": ["pkg/calc.py"],
        "_language": "python", "preferred_apply_method": "search_replace",
        "summary": "s", "risk": "low", "reason": "x"})
    snapshot = {"file_paths_sample": ["pkg/calc.py"], "repo_map": []}
    judge = {"accepted_candidates": ["candidate_01"]}
    metas = apply_hard_filter(run, [meta], judge, snapshot)
    assert metas[0].judge_status == "masked"  # placeholder는 accepted 불가
    assert "placeholder" in metas[0].judge_reason.lower()


def test_anchor_ambiguous_match_masked(tmp_path):
    # 실제 파일에서 search가 2회 매칭되면 masked(§17.1).
    proj = tmp_path / "proj"
    (proj / "pkg").mkdir(parents=True)
    (proj / "pkg" / "calc.py").write_text("x = 1\nx = 1\n", encoding="utf-8")
    run = create_run(proj)
    meta = write_patch_candidate(run, {
        "candidate_id": "candidate_01", "_target_files": ["pkg/calc.py"],
        "_language": "python", "preferred_apply_method": "search_replace",
        "summary": "s", "risk": "low", "reason": "x",
        "search_replace_edits": [{"file": "pkg/calc.py", "operation": "replace",
                                  "search": "x = 1", "replace": "x = 2"}]})
    snapshot = {"file_paths_sample": ["pkg/calc.py"], "repo_map": []}
    judge = {"accepted_candidates": ["candidate_01"]}
    metas = apply_hard_filter(run, [meta], judge, snapshot, project_path=proj)
    assert metas[0].judge_status == "masked"
    assert "2 locations" in metas[0].judge_reason


def test_tier_gating_downgrades_accept(tmp_path):
    proj = tmp_path / "proj"
    (proj / "pkg").mkdir(parents=True)
    (proj / "pkg" / "calc.py").write_text("return a\n", encoding="utf-8")
    run = create_run(proj)
    meta = write_patch_candidate(run, {
        "candidate_id": "candidate_01", "_target_files": ["pkg/calc.py"],
        "_language": "python", "preferred_apply_method": "search_replace",
        "summary": "s", "risk": "low", "reason": "x",
        "search_replace_edits": [{"file": "pkg/calc.py", "operation": "replace",
                                  "search": "return a", "replace": "return a + b"}]})
    snapshot = {"file_paths_sample": ["pkg/calc.py"], "repo_map": []}
    judge = {"accepted_candidates": ["candidate_01"]}
    metas = apply_hard_filter(run, [meta], judge, snapshot,
                              confidence_tier="medium", project_path=proj)
    assert metas[0].judge_status == "masked"  # tier<high면 draft_only


def test_preflight_packet_has_confidence_fields(sample_project, config):
    result = run_preflight(project_path=sample_project,
                           task="Add a subtract function to calc.py",
                           profile="standard", config=config, provider=MockProvider())
    packet = result["packet"]
    for f in ("confidence_tier", "evidence_score", "deterministic_signal_count",
              "fail_closed_triggered", "hard_gates_triggered", "context_pack_generated"):
        assert f in packet
    assert packet["confidence_tier"] in ("high", "medium", "low", "none")
