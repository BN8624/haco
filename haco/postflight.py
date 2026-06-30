# postflight: execution_result의 HACO Validation을 읽고 report.md / postflight_packet.json 생성.
from __future__ import annotations

import re
from pathlib import Path

from haco.candidate_store import write_fix_candidate
from haco.config import Config
from haco.model_client import ModelProvider, get_provider
from haco.schemas import (HacoEffectiveness, HacoValidation, PostflightPacket)
from haco.utils import read_json, read_text, write_json, write_text
from haco.workers import compact_snapshot, run_worker


def _parse_bool(val: str) -> bool:
    return val.strip().lower() in ("yes", "true", "y", "1")


def parse_haco_validation(execution_result: str) -> tuple[HacoValidation | None, bool]:
    """execution_result.md에서 HACO Validation 섹션을 파싱한다.

    반환: (validation 또는 None, 섹션_누락_여부)
    """
    if "HACO Validation" not in execution_result:
        return None, True

    # 섹션 이후 텍스트
    idx = execution_result.find("HACO Validation")
    section = execution_result[idx:]

    def field(name: str) -> str | None:
        m = re.search(rf"{name}\s*:\s*([^\n]*)", section, re.IGNORECASE)
        return m.group(1).strip() if m else None

    usefulness = field("candidate_usefulness") or "none"
    usefulness = usefulness.split()[0] if usefulness else "none"
    if usefulness not in ("usable", "partially_usable", "unusable", "none"):
        usefulness = "none"

    v = HacoValidation(
        task_packet_read=_parse_bool(field("task_packet_read") or "no"),
        accepted_candidates_checked=_parse_bool(
            field("accepted_candidates_checked") or "no"),
        candidate_usefulness=usefulness,
        bounded_exploration_needed=_parse_bool(
            field("bounded_exploration_needed") or "no"),
        reason=field("reason") or "",
    )
    return v, False


def _detect_test_outcome(run_path: Path) -> tuple[bool, bool | None]:
    """(tests_ran, tests_passed). 알 수 없으면 passed=None."""
    test_log = run_path / "test_log.txt"
    skipped = run_path / "tests_skipped.md"
    if test_log.exists():
        log = read_text(test_log).lower()
        if not log.strip():
            return True, None
        failed = any(w in log for w in ["failed", "error", "traceback",
                                        "assertionerror", "fail"])
        passed = any(w in log for w in ["passed", "ok", "0 failed", "success"])
        if failed and not passed:
            return True, False
        if passed and not failed:
            return True, True
        return True, None
    if skipped.exists():
        return False, None
    return False, None


def run_postflight(*, run_path: Path, project_path: Path | None,
                   config: Config, provider: ModelProvider | None = None) -> dict:
    run_path = Path(run_path)
    provider = provider or get_provider(config)

    packet = read_json(run_path / "task_packet.json", default={}) or {}
    execution_result = read_text(run_path / "execution_result.md")
    diff_summary = read_text(run_path / "diff_summary.md")

    validation, missing = parse_haco_validation(execution_result)
    tests_ran, tests_passed = _detect_test_outcome(run_path)

    # 실패 로그가 있으면 failure_fixer로 fix 후보 생성
    fix_candidates: list[str] = []
    if tests_ran and tests_passed is False:
        snapshot = read_json(run_path / "project_snapshot.json", default={}) or {}
        ctx = {"task": packet.get("compressed_context", ""),
               "worker": "failure_fixer",
               "snapshot": compact_snapshot(snapshot), "prior": {},
               "candidate_id": "candidate_fix_01"}
        out, _, _ = run_worker(provider, "failure_fixer", ctx, run_path, config)
        meta = write_fix_candidate(run_path, out)
        fix_candidates.append(meta.candidate_id)

    skip = packet.get("haco_status") == "skip_to_main_agent"
    pf = PostflightPacket(
        run_id=packet.get("run_id", run_path.name),
        project_path=str(project_path) if project_path else packet.get("project_path", ""),
        task_type=packet.get("task_type", "unknown"),
        haco_status=packet.get("haco_status", "ready"),
        skip_reason=packet.get("skip_reason", ""),
        suggested_haco_improvement=packet.get("suggested_haco_improvement", ""),
        haco_validation=validation or HacoValidation(),
        haco_effectiveness=HacoEffectiveness(
            main_agent_used_haco=bool(validation and validation.task_packet_read),
            skip_to_main_agent=skip,
            notes="" if validation else "No HACO Validation section found.",
        ),
        main_agent_did_not_record_haco_validation=missing,
        tests_ran=tests_ran,
        tests_passed=tests_passed,
        fix_candidates=fix_candidates,
    )
    write_json(run_path / "postflight_packet.json", pf.model_dump())

    # report.md
    v = pf.haco_validation
    tests_str = ("passed" if tests_passed else "failed") if tests_ran else "not run"
    report = "\n".join([
        "# HACO Report",
        "",
        f"- Task type: {pf.task_type}",
        f"- Changed: {diff_summary.strip()[:200] or '(see diff_summary.md)'}",
        f"- Tests: {tests_str}",
        f"- Result: {'fix candidate generated' if fix_candidates else 'completed'}",
        f"- Risk: {packet.get('risk', 'unknown')}",
        f"- Candidate usefulness: {v.candidate_usefulness}",
        f"- Bounded exploration: {str(v.bounded_exploration_needed).lower()}",
        f"- HACO validation recorded: {'no' if missing else 'yes'}",
        f"- Next action: "
        f"{'review fix candidate and rerun tests' if fix_candidates else 'none'}",
        "",
    ])
    write_text(run_path / "report.md", report)

    return {
        "run_path": str(run_path),
        "report": str(run_path / "report.md"),
        "postflight_packet": str(run_path / "postflight_packet.json"),
        "missing_validation": missing,
        "fix_candidates": fix_candidates,
    }
