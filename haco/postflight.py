# postflight: execution_result의 HACO Validation을 읽고 report.md / postflight_packet.json 생성.
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from haco.candidate_store import write_fix_candidate
from haco.config import Config
from haco.model_client import ModelProvider, get_provider
from haco.schemas import (HacoEffectiveness, HacoValidation, PostflightPacket)
from haco.utils import read_json, read_text, write_json, write_text
from haco.workers import compact_snapshot, run_worker


def _parse_bool(val: str) -> bool:
    return val.strip().lower() in ("yes", "true", "y", "1")


def _parse_int(val: str | None) -> int:
    m = re.search(r"-?\d+", val or "")
    return int(m.group()) if m else 0


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

    tier = (field("confidence_tier") or "none").split()[0]
    if tier not in ("high", "medium", "low", "none"):
        tier = "none"
    cp_read = (field("context_pack_read") or "not_present").split()[0]
    if cp_read not in ("yes", "no", "not_present"):
        cp_read = "not_present"

    v = HacoValidation(
        haco_used=_parse_bool(field("haco_used") or "no"),
        task_packet_read=_parse_bool(field("task_packet_read") or "no"),
        execution_brief_read=_parse_bool(field("execution_brief_read") or "no"),
        context_pack_read=cp_read,
        accepted_candidates_checked=_parse_bool(
            field("accepted_candidates_checked") or "no"),
        candidate_usefulness=usefulness,
        bounded_exploration_needed=_parse_bool(
            field("bounded_exploration_needed") or "no"),
        fail_closed_triggered=_parse_bool(field("fail_closed_triggered") or "no"),
        fail_closed_reason=field("fail_closed_reason") or "",
        confidence_tier=tier,
        evidence_score=_parse_int(field("evidence_score")),
        deterministic_signal_count=_parse_int(field("deterministic_signal_count")),
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
        # pytest 요약의 'N failed' / 'N error(s)'를 우선 신뢰한다. 통과 테스트와 공존해도
        # ('1 failed, 71 passed') 카운트로 정확히 판정된다. 0이면 통과, >0이면 실패.
        fail_counts = [int(n) for n in re.findall(r"(\d+)\s+(?:failed|errors?)", log)]
        if fail_counts:
            return True, sum(fail_counts) == 0
        # pytest 카운트가 없으면 'status: PASS' / 'status FAIL' 같은 명시적 최종 상태 라인을
        # 신뢰한다. pytest를 안 쓰는 자체 verifier가 흔히 쓰는 관례다. 여러 라인이면 전부 pass라야 통과.
        status_marks = re.findall(r"status\s*:?\s+(pass|fail)\b", log)
        if status_marks:
            return True, all(m == "pass" for m in status_marks)
        # 카운트도 상태 라인도 없으면 명시적 실패 마커로 판정한다. 단독 'error'/'fail'은 테스트명 오탐이
        # 잦아 제외하고, 강한 신호만 쓴다.
        if any(w in log for w in ("failed", "traceback", "assertionerror")):
            return True, False
        if "passed" in log or "success" in log or re.search(r"\bok\b", log):
            return True, True
        return True, None
    if skipped.exists():
        return False, None
    return False, None


def build_auto_diff_summary(project_path: Path | None) -> str:
    """git으로 작업트리 변경을 결정론적으로 요약한다(§7.3 auto_diff_summary).

    에이전트가 쓴 diff_summary.md와 별개로 HACO가 직접 만드는 확정 요약이다.
    git이 없거나 커밋 후라 변경이 없으면 정직하게 그 사실을 적는다.
    """
    if not project_path:
        return "# Auto diff summary\n\n(no project path; cannot compute git diff)\n"

    def _git(*args: str) -> tuple[int, str]:
        try:
            p = subprocess.run(["git", "-C", str(project_path), *args],
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=15)
            return p.returncode, p.stdout
        except Exception:
            return 1, ""

    rc, stat = _git("diff", "--stat", "HEAD")
    if rc != 0:
        return "# Auto diff summary\n\n(not a git repository or git unavailable)\n"
    _, status = _git("status", "--porcelain")
    untracked = [ln for ln in status.splitlines() if ln.startswith("??")]

    body = ["# Auto diff summary", "",
            "Deterministic git working-tree summary produced by HACO.", ""]
    if stat.strip():
        body += ["```", stat.strip(), "```", ""]
    else:
        body += ["- No uncommitted changes vs HEAD "
                 "(the agent may have already committed; see diff_summary.md).", ""]
    if untracked:
        body.append(f"- Untracked files: {len(untracked)}")
    return "\n".join(body) + "\n"


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
        fail_closed_triggered=bool(packet.get("fail_closed_triggered", False)),
        fail_closed_reason=packet.get("fail_closed_reason", ""),
        confidence_tier=packet.get("confidence_tier", "none"),
        evidence_score=int(packet.get("evidence_score", 0) or 0),
        deterministic_signal_count=int(packet.get("deterministic_signal_count", 0) or 0),
        tests_ran=tests_ran,
        tests_passed=tests_passed,
        fix_candidates=fix_candidates,
    )
    write_json(run_path / "postflight_packet.json", pf.model_dump())

    # auto_diff_summary.md — HACO가 직접 만드는 결정론적 diff 요약(§7.3)
    auto_diff = build_auto_diff_summary(project_path)
    write_text(run_path / "auto_diff_summary.md", auto_diff)

    # report.md
    v = pf.haco_validation
    if not tests_ran:
        tests_str = "not run"
    elif tests_passed is None:
        tests_str = "unknown"
    else:
        tests_str = "passed" if tests_passed else "failed"
    report = "\n".join([
        "# HACO Report",
        "",
        f"- Task type: {pf.task_type}",
        f"- Changed: {diff_summary.strip()[:200] or '(see diff_summary.md)'}",
        f"- Tests: {tests_str}",
        f"- Confidence: {pf.confidence_tier} (evidence={pf.evidence_score}, "
        f"signals={pf.deterministic_signal_count}, "
        f"fail_closed={str(pf.fail_closed_triggered).lower()})",
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
        "auto_diff_summary": str(run_path / "auto_diff_summary.md"),
        "missing_validation": missing,
        "fix_candidates": fix_candidates,
    }
