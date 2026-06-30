# aggregate: risk max, new_doc_needed 기본, user_decision_needed, skip 처리.
from haco.aggregate import build_task_packet
from haco.schemas import CandidateSummary


def _outputs(**over):
    base = {
        "task_router": {"task_type": "code_change", "risk": "medium",
                        "user_decision_needed": False,
                        "recommended_mode": "candidate_generation", "reason": "r"},
        "context_compressor": {"compressed_context": "ctx", "known_constraints": [],
                               "assumptions": ["a"]},
        "file_locator": {"files_to_read": ["a.py"], "files_to_edit": ["a.py"],
                         "search_keywords": ["k"], "confidence": "medium",
                         "reason": "loc"},
        "test_candidate": {"test_scope": "focused", "tests_to_run": ["pytest"]},
        "doc_reporter": {"new_doc_needed": False, "docs_to_update": []},
        "patch_candidate": {"risk": "high"},
    }
    base.update(over)
    return base


def _build(outputs, core_failed=None, skip=False, skip_reason=""):
    return build_task_packet(
        run_id="r1", project_path="/x", outputs=outputs,
        core_failed=core_failed or [], skip=skip, skip_reason=skip_reason,
        locator_passes=1, locator_rescan_applied=False, locator_rescan_notes=[],
        candidate_summary=CandidateSummary(), suggested_improvement="imp")


def test_risk_takes_max():
    p = _build(_outputs())
    assert p.risk == "high"  # patch_candidate risk=high overrides router medium


def test_new_doc_needed_default_false():
    p = _build(_outputs())
    assert p.new_doc_needed is False


def test_user_decision_needed_from_router():
    out = _outputs(task_router={"task_type": "refactor", "risk": "high",
                                "user_decision_needed": True,
                                "recommended_mode": "candidate_generation"})
    p = _build(out)
    assert p.user_decision_needed is True


def test_skip_sets_status_and_reason():
    p = _build(_outputs(), core_failed=["file_locator"], skip=True,
               skip_reason="locator_failed")
    assert p.haco_status == "skip_to_main_agent"
    assert p.skip_reason == "locator_failed"
    assert p.suggested_haco_improvement == "imp"


def test_tests_and_files_follow_workers():
    p = _build(_outputs())
    assert p.tests_to_run == ["pytest"]
    assert p.files_to_edit == ["a.py"]
