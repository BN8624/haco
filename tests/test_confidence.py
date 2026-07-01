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


def test_symbol_evidence_requires_symbols(config):
    # repo_map에 파일은 있으나 symbols가 비어 있으면 symbol_evidence를 주지 않는다.
    snap = {"file_paths_sample": ["a.py"], "repo_map": [{"file": "a.py", "symbols": []}],
            "keyword_file_matches": ["a.py"]}
    d = evaluate_confidence(snapshot=snap, locator={"files_to_read": ["a.py"],
                                                    "search_keywords": ["x"]},
                            context_pack_json=_cp(1), task_type="code_change",
                            config=config)
    assert "symbol_evidence" not in d["signals"]


def test_keyword_evidence_requires_window(config):
    # snapshot에 keyword_file_matches가 있어도 context_pack에 keyword_window가 없으면
    # keyword_evidence를 주지 않는다(무관한 match로 점수 부풀림 방지).
    snap = {"file_paths_sample": ["a.py"],
            "repo_map": [{"file": "a.py", "symbols": [
                {"kind": "function", "name": "f", "line_start": 1, "line_end": 3}]}],
            "keyword_file_matches": ["a.py"]}
    cp = {"files": [{"kind": "symbol"}], "budget": {"token_estimate": 50, "max_tokens": 8000}}
    d = evaluate_confidence(snapshot=snap, locator={"files_to_read": ["a.py"],
                                                    "search_keywords": ["zzz"]},
                            context_pack_json=cp, task_type="code_change", config=config)
    assert "keyword_evidence" not in d["signals"]


def test_keyword_evidence_when_window_present(config):
    snap = {"file_paths_sample": ["a.py"], "repo_map": []}
    cp = {"files": [{"kind": "keyword_window"}],
          "budget": {"token_estimate": 50, "max_tokens": 8000}}
    d = evaluate_confidence(snapshot=snap, locator={"files_to_read": ["a.py"],
                                                    "search_keywords": ["x"]},
                            context_pack_json=cp, task_type="code_change", config=config)
    assert "keyword_evidence" in d["signals"]


def test_exact_symbol_evidence_stronger_than_signature(config):
    # exact_name 매칭은 strong_symbol_evidence(가점 25), signature-only 는 weak(가점 10).
    snap = {"file_paths_sample": ["a.py"],
            "repo_map": [{"file": "a.py", "symbols": [
                {"kind": "function", "name": "target_fn",
                 "line_start": 1, "line_end": 3}]}]}
    loc = {"files_to_read": ["a.py"], "search_keywords": ["target_fn"]}
    cp_exact = {"files": [{"kind": "symbol", "match_tier": "exact_name"}],
                "budget": {"token_estimate": 50, "max_tokens": 8000}}
    cp_sig = {"files": [{"kind": "symbol", "match_tier": "signature"}],
              "budget": {"token_estimate": 50, "max_tokens": 8000}}
    d_exact = evaluate_confidence(snapshot=snap, locator=loc, context_pack_json=cp_exact,
                                  task_type="code_change", config=config)
    d_sig = evaluate_confidence(snapshot=snap, locator=loc, context_pack_json=cp_sig,
                                task_type="code_change", config=config)
    assert "strong_symbol_evidence" in d_exact["signals"]
    assert "weak_symbol_evidence" in d_sig["signals"]
    assert d_exact["evidence_score"] > d_sig["evidence_score"]


def test_fullblock_missing_symbol_not_accepted(tmp_path):
    # full_block target symbol이 repo_map에 없으면 high confidence여도 masked.
    run = create_run(tmp_path)
    meta = write_patch_candidate(run, {
        "candidate_id": "candidate_01", "_target_files": ["pkg/calc.py"],
        "_language": "python", "preferred_apply_method": "full_block",
        "summary": "s", "risk": "low", "reason": "x",
        "replacement_blocks": [{"file": "pkg/calc.py", "target": "ghost_fn",
                                "language": "python", "code": "def ghost_fn(): pass",
                                "apply_method": "replace entire function"}]})
    snapshot = {"file_paths_sample": ["pkg/calc.py"],
                "repo_map": [{"file": "pkg/calc.py", "symbols": [
                    {"kind": "function", "name": "add"}]}]}
    judge = {"accepted_candidates": ["candidate_01"]}
    metas = apply_hard_filter(run, [meta], judge, snapshot)  # tier 기본 high
    assert metas[0].judge_status == "masked"
    assert "not found" in metas[0].judge_reason


def test_fullblock_existing_symbol_can_accept(tmp_path):
    run = create_run(tmp_path)
    meta = write_patch_candidate(run, {
        "candidate_id": "candidate_01", "_target_files": ["pkg/calc.py"],
        "_language": "python", "preferred_apply_method": "full_block",
        "summary": "s", "risk": "low", "reason": "x",
        "replacement_blocks": [{"file": "pkg/calc.py", "target": "add",
                                "language": "python", "code": "def add(a,b): return a+b",
                                "apply_method": "replace entire function"}]})
    snapshot = {"file_paths_sample": ["pkg/calc.py"],
                "repo_map": [{"file": "pkg/calc.py", "symbols": [
                    {"kind": "function", "name": "add"}]}]}
    judge = {"accepted_candidates": ["candidate_01"]}
    metas = apply_hard_filter(run, [meta], judge, snapshot)
    assert metas[0].judge_status == "accepted"


def test_fail_closed_skip_disables_doc_and_context(empty_project, config):
    # skip(저신뢰/locator 실패)이면 doc_reporter를 돌리지 않고 context_pack은 비며
    # context_pack_generated=False가 되어야 한다(저신뢰 출력은 짧아야 함).
    import json
    result = run_preflight(project_path=empty_project, task="add subtract function",
                           profile="standard", config=config, provider=MockProvider())
    run = Path(result["run_path"])
    assert result["packet"]["haco_status"] == "skip_to_main_agent"
    assert not (run / "worker_outputs" / "doc_reporter.json").exists()
    cp = json.loads((run / "context_pack.json").read_text(encoding="utf-8"))
    assert cp["files"] == []
    assert result["packet"]["context_pack_generated"] is False


def test_preflight_packet_has_confidence_fields(sample_project, config):
    result = run_preflight(project_path=sample_project,
                           task="Add a subtract function to calc.py",
                           profile="standard", config=config, provider=MockProvider())
    packet = result["packet"]
    for f in ("confidence_tier", "evidence_score", "deterministic_signal_count",
              "fail_closed_triggered", "hard_gates_triggered", "context_pack_generated"):
        assert f in packet
    assert packet["confidence_tier"] in ("high", "medium", "low", "none")
