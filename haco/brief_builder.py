# execution_brief.md 생성. 메인 코딩 에이전트가 작업 전에 읽는 실행 브리프.
from __future__ import annotations

import json
from pathlib import Path

from haco.schemas import CandidateMetadata, TaskPacket

_VALIDATION_TEMPLATE = """```text
## HACO Validation

haco_used: yes/no
haco_skip_reason: none/trivial/no_repo_file_work/uploaded_file_review/unavailable/not_cost_effective/other
haco_skip_approved_by_user: yes/no/not_applicable
haco_status: completed/skip_to_main_agent/failed
fail_closed_triggered: yes/no
fail_closed_reason:
confidence_tier: high/medium/low/none
evidence_score:
deterministic_signal_count:
task_packet_read: yes/no
execution_brief_read: yes/no
context_pack_read: yes/no/not_present
accepted_candidates_checked: yes/no
candidate_usefulness: usable | partially_usable | unusable | none
bounded_exploration_needed: yes/no
reason:
```"""

_DEFAULT_RUN = ".haco/runs/latest"
_DEFAULT_PROJECT = "."


def build_postflight_command(run_path: str | Path | None,
                             project_path: str | None) -> str:
    """완성된 postflight 명령 문자열을 만든다. 인자가 비면 기본값으로 채워 빈 인자를 막는다."""
    run = (str(run_path).strip() if run_path is not None else "") or _DEFAULT_RUN
    proj = (str(project_path).strip() if project_path is not None else "") or _DEFAULT_PROJECT
    return f"python -m haco postflight --run {run} --project {proj}"


def build_execution_brief(packet: TaskPacket, metas: list[CandidateMetadata],
                          run_path: Path) -> str:
    accepted = [m for m in metas if m.judge_status == "accepted"]
    masked = [m for m in metas if m.judge_status == "masked"]

    skip = packet.haco_status == "skip_to_main_agent"

    lines: list[str] = []
    lines.append("# HACO Execution Brief")
    lines.append("")
    lines.append("You are the main coding agent.")
    lines.append("")
    lines.append("HACO has prepared a task packet and candidate files to reduce your "
                 "exploration cost.")
    lines.append("")

    # HACO가 결정론 신호로 산출한 confidence(§17.1). LLM self-report이 아니다.
    lines.append("## HACO confidence (computed by HACO, not self-reported)")
    lines.append("")
    lines.append(f"- confidence_tier: {packet.confidence_tier}")
    lines.append(f"- evidence_score: {packet.evidence_score}")
    lines.append(f"- deterministic_signal_count: {packet.deterministic_signal_count}")
    lines.append(f"- fail_closed_triggered: {str(packet.fail_closed_triggered).lower()}")
    if packet.hard_gates_triggered:
        lines.append(f"- hard_gates_triggered: {', '.join(packet.hard_gates_triggered)}")
    lines.append("")

    if skip:
        lines.append("> HACO could not prepare reliable candidates.")
        lines.append("> Do not rely on candidates.")
        lines.append("> Proceed with normal bounded exploration.")
        lines.append("")
        lines.append(f"skip_reason: {packet.skip_reason}")
        lines.append("")

    lines.append("## Mandatory first step")
    lines.append("")
    lines.append("Before editing files, validate HACO outputs.")
    lines.append("Record the result in `execution_result.md` under a section named "
                 "`HACO Validation`.")
    lines.append("")
    lines.append("You must check:")
    lines.append("")
    lines.append("- Did you read `task_packet.json`?")
    lines.append("- Did you inspect accepted candidates?")
    lines.append("- Are the suggested files plausible?")
    lines.append("- Are the candidates usable, partially usable, or unusable?")
    lines.append("- If you perform broader exploration, why was it necessary?")
    lines.append("")
    lines.append("Use this format:")
    lines.append("")
    lines.append(_VALIDATION_TEMPLATE)
    lines.append("")

    lines.append("## Required behavior")
    lines.append("")
    lines.append("- Read `context_pack.md` first — focused excerpts with line ranges "
                 "so you can avoid reading whole files.")
    lines.append("- Then read `task_packet.json`.")
    lines.append("- Read the suggested files only where the context pack is insufficient.")
    lines.append("- Check accepted candidates before writing a patch from scratch.")
    if packet.prior_change_reference:
        lines.append(f"- Read `{packet.prior_change_reference}` — the prior similar change "
                     f"to your edit target; use it as a template, not a blind copy.")
    lines.append("- If a candidate is usable, apply or adapt it.")
    lines.append("- If a candidate is wrong, do not blindly follow it.")
    lines.append("- Do not treat `optional.diff` as the primary source of truth.")
    lines.append("- Prefer `edit_plan.md`, `search_replace.json`, and "
                 "`replacement_blocks.md` over raw diff.")
    lines.append(f"- Do not create new documents unless new_doc_needed=true "
                 f"(currently {str(packet.new_doc_needed).lower()}).")
    lines.append(f"- Use the recommended test scope: {packet.test_scope}.")
    lines.append(f"- Do not ask the user if user_decision_needed=false "
                 f"(currently {str(packet.user_decision_needed).lower()}).")
    lines.append("- Keep edits minimal.")
    lines.append("- Avoid broad refactors unless the task requires them.")
    lines.append("- After execution, write `execution_result.md`.")
    lines.append("- Write `diff_summary.md`.")
    lines.append("- If tests ran, write `test_log.txt`.")
    lines.append("- If tests were skipped, write `tests_skipped.md`.")
    lines.append(f"- Then run `{build_postflight_command(_DEFAULT_RUN, packet.project_path)}`.")
    lines.append("- Keep final report short.")
    lines.append("")

    lines.append("## Bounded exploration rule")
    lines.append("")
    lines.append("Use HACO outputs first.")
    lines.append("Do not perform broad exploration before checking task_packet and "
                 "accepted candidates.")
    lines.append("")
    lines.append("If HACO candidates are missing, low confidence, or clearly wrong, "
                 "perform bounded exploration:")
    lines.append("- start from files_to_read and search_keywords")
    lines.append("- use focused search")
    lines.append("- avoid full repository scans unless necessary")
    lines.append("- explain briefly why broader exploration was needed")
    lines.append("")

    lines.append("## Task packet")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(packet.model_dump(), ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")

    lines.append("## Accepted candidate files")
    lines.append("")
    if accepted:
        for m in accepted:
            lines.append(f"- `candidates/{m.candidate_id}/` "
                         f"(kind={m.kind}, method={m.preferred_apply_method}) — "
                         f"{m.summary}")
    else:
        lines.append("- (none accepted)")
    lines.append("")

    lines.append("## Masked candidates")
    lines.append("")
    if masked:
        lines.append(f"{len(masked)} additional candidates exist but were masked by HACO.")
    else:
        lines.append("None.")
    lines.append("")

    lines.append("## Output files required after execution")
    lines.append("")
    lines.append("- execution_result.md")
    lines.append("- diff_summary.md")
    lines.append("- test_log.txt or tests_skipped.md")
    lines.append("")

    return "\n".join(lines)
