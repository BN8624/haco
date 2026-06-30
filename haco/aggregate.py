# worker 결과를 합쳐 task_packet.json을 만든다. risk max, skip 판단, fallback 규칙.
from __future__ import annotations

from haco.schemas import CandidateSummary, TaskPacket
from haco.utils import clamp_str

RISK_ORDER = {"low": 0, "medium": 1, "high": 2}

WORKER_OUTPUT_PATHS = {
    "task_router": "worker_outputs/task_router.json",
    "context_compressor": "worker_outputs/context_compressor.json",
    "file_locator": "worker_outputs/file_locator.json",
    "patch_candidate": "worker_outputs/patch_candidate.json",
    "test_candidate": "worker_outputs/test_candidate.json",
    "doc_reporter": "worker_outputs/doc_reporter.json",
    "candidate_judge": "worker_outputs/candidate_judge.json",
}


def _max_risk(*risks: str) -> str:
    best = "low"
    for r in risks:
        if RISK_ORDER.get(r, 0) > RISK_ORDER.get(best, 0):
            best = r
    return best


def build_task_packet(*, run_id: str, project_path: str, outputs: dict[str, dict],
                      core_failed: list[str], skip: bool, skip_reason: str,
                      locator_passes: int, locator_rescan_applied: bool,
                      locator_rescan_notes: list[str],
                      candidate_summary: CandidateSummary | None,
                      suggested_improvement: str = "",
                      prior_change_reference: str = "") -> TaskPacket:
    router = outputs.get("task_router", {})
    compressor = outputs.get("context_compressor", {})
    locator = outputs.get("file_locator", {})
    tester = outputs.get("test_candidate", {})
    doc = outputs.get("doc_reporter", {})
    patch = outputs.get("patch_candidate", {})

    risk = _max_risk(router.get("risk", "medium"), patch.get("risk", "low"))

    test_scope = tester.get("test_scope", "unknown")
    long_run = test_scope == "long_run"

    haco_status = "skip_to_main_agent" if skip else "ready"
    if skip:
        recommended_action = ("Main coding agent should proceed directly with normal "
                              "bounded exploration; HACO candidates are unreliable.")
    else:
        recommended_action = ("Read task_packet and accepted candidates first, then "
                              "apply minimal changes and run the recommended tests.")

    reason_bits = [router.get("reason", ""), locator.get("reason", "")]
    reason = clamp_str(" ".join(b for b in reason_bits if b), 800)

    packet = TaskPacket(
        run_id=run_id,
        project_path=project_path,
        haco_status=haco_status,
        skip_reason=skip_reason if skip else "",
        suggested_haco_improvement=suggested_improvement if skip else "",
        locator_passes=locator_passes,
        locator_rescan_applied=locator_rescan_applied,
        locator_rescan_notes=locator_rescan_notes,
        task_type=router.get("task_type", "unknown"),
        user_decision_needed=bool(router.get("user_decision_needed", False)),
        risk=risk,
        recommended_mode=router.get("recommended_mode", "candidate_generation"),
        compressed_context=clamp_str(compressor.get("compressed_context", ""), 2000),
        files_to_read=locator.get("files_to_read", []) or [],
        files_to_edit=locator.get("files_to_edit", []) or [],
        search_keywords=locator.get("search_keywords", []) or [],
        tests_to_run=tester.get("tests_to_run", []) or [],
        test_scope=test_scope,
        long_run_needed=long_run,
        docs_to_update=doc.get("docs_to_update", []) or [],
        new_doc_needed=bool(doc.get("new_doc_needed", False)),
        candidate_summary=candidate_summary or CandidateSummary(),
        prior_change_reference=prior_change_reference,
        constraints=compressor.get("known_constraints", []) or [],
        assumptions=compressor.get("assumptions", []) or [],
        recommended_action=recommended_action,
        reason=reason,
        worker_outputs={k: v for k, v in WORKER_OUTPUT_PATHS.items()
                        if k in outputs},
    )
    return packet
