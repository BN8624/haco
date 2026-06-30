# execution_brief.md 생성. 메인 코딩 에이전트가 작업 전에 읽는 실행 브리프.
from __future__ import annotations

import json
from pathlib import Path

from haco.schemas import CandidateMetadata, TaskPacket

_VALIDATION_TEMPLATE = """```text
## HACO Validation

task_packet_read: yes/no
accepted_candidates_checked: yes/no
candidate_usefulness: usable | partially_usable | unusable | none
bounded_exploration_needed: yes/no
reason:
```"""


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
    lines.append("- Read `task_packet.json` first.")
    lines.append("- Read the suggested files first.")
    lines.append("- Check accepted candidates before writing a patch from scratch.")
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
    lines.append("- Then run "
                 "`python -m haco postflight --run <this_run_dir> --project <project_path>`.")
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
