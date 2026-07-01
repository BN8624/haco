# candidate 디렉터리 저장과 hard filtering. HACO는 후보를 직접 적용하지 않는다.
from __future__ import annotations

from pathlib import Path

from haco.schemas import CandidateMetadata, CandidateSummary
from haco.utils import read_json, read_text, write_json, write_text


def _candidates_dir(run_path: Path) -> Path:
    d = Path(run_path) / "candidates"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _as_dict(item) -> dict:
    """worker output의 항목을 dict로 정규화한다(model_dump 결과는 이미 dict)."""
    if isinstance(item, dict):
        return item
    if hasattr(item, "model_dump"):
        return item.model_dump()
    return {}


def write_patch_candidate(run_path: Path, output: dict) -> CandidateMetadata:
    """patch_candidate worker 출력으로 candidate 디렉터리를 만든다."""
    cid = output.get("candidate_id", "candidate_01")
    targets = output.get("_target_files", []) or []
    language = output.get("_language", "unknown")
    method = output.get("preferred_apply_method", "strategy_only")
    summary = output.get("summary", "")
    risk = output.get("risk", "medium")

    cdir = _candidates_dir(run_path) / cid
    cdir.mkdir(parents=True, exist_ok=True)

    kind = "patch" if targets else "strategy"
    meta = CandidateMetadata(
        candidate_id=cid,
        kind=kind,
        target_files=targets,
        language=language,
        confidence="medium" if targets else "low",
        preferred_apply_method=method,
        summary=summary,
        risk=risk,
        reason=output.get("reason", ""),
    )
    write_json(cdir / "candidate.json", meta.model_dump())

    # 실제 worker 후보 내용(있으면 보존, 없으면 skeleton 폴백)
    edit_plan = (output.get("edit_plan") or "").strip()
    sr_edits = output.get("search_replace_edits") or []
    repl_blocks = output.get("replacement_blocks") or []

    # edit_plan.md — 실제 plan이 있으면 그대로, 없으면 기존 skeleton
    if edit_plan:
        write_text(cdir / "edit_plan.md", f"# Edit Plan: {cid}\n\n{edit_plan}\n")
    else:
        plan_lines = [
            f"# Edit Plan: {cid}",
            "",
            f"## Goal", summary or "(see task)",
            "",
            "## Target files",
        ]
        if targets:
            plan_lines += [f"- `{t}`" for t in targets]
        else:
            plan_lines.append("- (uncertain — strategy only)")
        plan_lines += [
            "",
            "## Apply order",
            f"- preferred method: {method}",
            "",
            "## Notes for the main agent",
            "- Review before applying. HACO does not apply this directly.",
            "- Prefer edit_plan/search_replace/replacement_blocks over optional.diff.",
        ]
        write_text(cdir / "edit_plan.md", "\n".join(plan_lines) + "\n")

    # search_replace.json — 실제 edit이 있으면 그대로, 없고 target만 있으면 skeleton
    if sr_edits:
        edits = []
        for e in sr_edits:
            e = _as_dict(e)
            edits.append({
                "file": e.get("file", ""),
                "operation": e.get("operation", "replace"),
                "search": e.get("search", ""),
                "replace": e.get("replace", ""),
                "notes": e.get("notes", ""),
            })
        write_json(cdir / "search_replace.json", {"edits": edits})
    elif targets:
        write_json(cdir / "search_replace.json", {
            "edits": [
                {
                    "file": targets[0],
                    "operation": "replace",
                    "search": "<<< exact block to find in the file >>>",
                    "replace": "<<< new block >>>",
                    "notes": "Filled by worker; main agent must verify against real file.",
                }
            ]
        })

    # replacement_blocks.md — 실제 block이 있으면 그대로, 없고 target만 있으면 skeleton
    if repl_blocks:
        blocks_md: list[str] = []
        for i, b in enumerate(repl_blocks, 1):
            b = _as_dict(b)
            blang = b.get("language", "unknown")
            fence = blang if blang and blang != "unknown" else ""
            blocks_md.append(
                f"## Replacement {i}\n\n"
                f"File: {b.get('file', '')}  \n"
                f"Target: {b.get('target', '')}  \n"
                f"Apply method: {b.get('apply_method', 'replace entire function')}\n\n"
                f"```{fence}\n{b.get('code', '')}\n```\n")
        write_text(cdir / "replacement_blocks.md", "\n".join(blocks_md))
    elif targets:
        write_text(cdir / "replacement_blocks.md",
                   f"## Replacement 1\n\nFile: {targets[0]}  \n"
                   f"Target: (function/class to identify)  \n"
                   f"Apply method: replace target block\n\n"
                   f"```{language if language != 'unknown' else ''}\n"
                   f"# main agent: insert verified replacement here\n```\n")
    return meta


def write_test_candidate(run_path: Path, output: dict, base_cid: str) -> CandidateMetadata | None:
    """test_candidate 출력을 candidate 디렉터리에 기록한다."""
    cid = base_cid
    cdir = _candidates_dir(run_path) / cid
    cdir.mkdir(parents=True, exist_ok=True)
    language = output.get("_language", "unknown")
    scope = output.get("test_scope", "unknown")

    meta = CandidateMetadata(
        candidate_id=cid,
        kind="test",
        target_files=[],
        language=language,
        confidence="low" if language == "unknown" else "medium",
        preferred_apply_method="strategy_only",
        summary=f"Test scope: {scope}",
        risk="low",
        reason=output.get("reason", ""),
    )
    write_json(cdir / "candidate.json", meta.model_dump())

    if language == "unknown":
        write_text(cdir / "test_candidate.md",
                   f"# Test Strategy\n\nLanguage unknown; do not fabricate test code.\n"
                   f"Scope: {scope}\n"
                   f"Suggested approach: run existing tests if any, add focused tests "
                   f"after confirming language and framework.\n")
    else:
        write_text(cdir / "test_candidate.md",
                   f"# Test Strategy ({language})\n\nScope: {scope}\n"
                   f"Tests to run: {', '.join(output.get('tests_to_run', [])) or '(none detected)'}\n")
    return meta


def write_fix_candidate(run_path: Path, output: dict) -> CandidateMetadata:
    """failure_fixer 출력을 fix candidate 디렉터리에 기록한다."""
    cid = output.get("fix_candidate_id", "candidate_fix_01")
    cdir = _candidates_dir(run_path) / cid
    cdir.mkdir(parents=True, exist_ok=True)
    meta = CandidateMetadata(
        candidate_id=cid,
        kind="fix",
        target_files=[],
        confidence="low",
        preferred_apply_method="strategy_only",
        summary=output.get("likely_cause", ""),
        risk="medium",
        reason=output.get("reason", ""),
    )
    write_json(cdir / "candidate.json", meta.model_dump())
    write_text(cdir / "edit_plan.md",
               f"# Fix Plan: {cid}\n\n## Likely cause\n{output.get('likely_cause', '')}\n\n"
               f"## Tests to rerun\n" +
               "\n".join(f"- {t}" for t in output.get("tests_to_rerun", [])) + "\n")
    return meta


# ----------------------------- Hard filtering -----------------------------

def _anchor_blocks_accept(run_path: Path, cid: str,
                          project_path: Path | None) -> str | None:
    """search_replace anchor 검증. accepted 불가 사유가 있으면 문자열, 없으면 None.

    §17.1 Fail Closed: placeholder/빈 replace/anchor 0회·다회 매칭은 accepted가 될 수 없다.
    project_path가 있고 target 파일이 실재할 때만 실제 매칭 횟수를 확인한다(없으면 placeholder만 검사).
    """
    sr = read_json(Path(run_path) / "candidates" / cid / "search_replace.json",
                   default=None)
    if not sr or not sr.get("edits"):
        return None  # search_replace 후보가 아니면 이 규칙 대상 아님
    for e in sr["edits"]:
        search = e.get("search", "")
        replace = e.get("replace", "")
        op = e.get("operation", "replace")
        if "<<<" in search or "<<<" in replace:
            return "search/replace is a placeholder skeleton"
        if not search.strip():
            return "empty search anchor"
        if op == "replace" and not replace.strip():
            return "empty replacement for a replace operation"
        if project_path is not None:
            target = Path(project_path) / e.get("file", "")
            if target.is_file():
                try:
                    count = read_text(target).count(search)
                except OSError:
                    count = -1
                if count == 0:
                    return "search anchor matches zero locations"
                if count > 1:
                    return f"search anchor matches {count} locations (ambiguous)"
    return None


def apply_hard_filter(run_path: Path, metas: list[CandidateMetadata],
                      judge: dict, snapshot: dict, *,
                      confidence_tier: str = "high",
                      project_path: Path | None = None) -> list[CandidateMetadata]:
    """judge 결과 + 규칙으로 candidate 상태를 확정하고 candidate.json을 갱신한다.

    confidence_tier가 high가 아니면 accepted를 masked로 강등한다(§17.1: medium은 draft_only).
    anchor 검증에 실패한 후보도 accepted가 될 수 없다.
    """
    accepted = set(judge.get("accepted_candidates", []) or [])
    masked = set(judge.get("masked_candidates", []) or [])
    rejected = set(judge.get("rejected_candidates", []) or [])

    known_paths = set(snapshot.get("file_paths_sample", []) or [])
    for item in snapshot.get("repo_map", []) or []:
        if isinstance(item, dict) and item.get("file"):
            known_paths.add(item["file"])

    for meta in metas:
        cid = meta.candidate_id
        status = "masked"
        if cid in rejected:
            status = "rejected"
        elif cid in accepted:
            status = "accepted"
        elif cid in masked:
            status = "masked"
        else:
            status = "masked"

        # 규칙 기반 hard filter (judge보다 보수적으로 강등 가능)
        # 적용 방법이 strategy_only가 아닌데 target_files가 없으면 적용 불가 → reject.
        if meta.kind != "test" and not meta.target_files and \
                meta.preferred_apply_method != "strategy_only":
            status = "rejected"
            meta.judge_reason = "No target files but apply method is not strategy_only."
        elif meta.target_files and known_paths and \
                not any(t in known_paths for t in meta.target_files):
            # snapshot에 전혀 없는 경로 → 강등
            if status == "accepted":
                status = "masked"
                meta.judge_reason = "Target files not found in snapshot/repo_map."

        # anchor 검증: placeholder/빈 replace/0회·다회 매칭이면 accepted 불가(§17.1).
        if status == "accepted":
            anchor_reason = _anchor_blocks_accept(run_path, cid, project_path)
            if anchor_reason:
                status = "masked"
                meta.judge_reason = f"Anchor check failed: {anchor_reason}."

        # confidence tier가 high가 아니면 accepted를 draft_only로 강등(§17.1).
        if status == "accepted" and confidence_tier != "high":
            status = "masked"
            meta.judge_reason = (f"Confidence tier is {confidence_tier}; "
                                 f"candidate kept as draft, not accepted.")

        meta.judge_status = status
        meta.expose_in_execution_brief = (status == "accepted")
        if not meta.judge_reason:
            meta.judge_reason = {
                "accepted": "Plausible and worth reviewing first.",
                "masked": "Kept for reference, not surfaced in brief.",
                "rejected": "Filtered out as low quality.",
            }[status]

        # candidate.json 갱신
        cdir = Path(run_path) / "candidates" / cid
        if cdir.exists():
            write_json(cdir / "candidate.json", meta.model_dump())

        # rejected는 rejected/ 폴더로 이동
        if status == "rejected" and cdir.exists():
            rej_root = Path(run_path) / "candidates" / "rejected"
            rej_root.mkdir(parents=True, exist_ok=True)
            target = rej_root / cid
            if target.exists():
                continue
            cdir.rename(target)

    return metas


def build_candidate_summary(metas: list[CandidateMetadata], judge: dict) -> CandidateSummary:
    patch = [m.candidate_id for m in metas if m.kind in ("patch", "strategy")]
    tests = [m.candidate_id for m in metas if m.kind == "test"]
    fixes = [m.candidate_id for m in metas if m.kind == "fix"]
    return CandidateSummary(
        generated=len(metas),
        accepted=sum(1 for m in metas if m.judge_status == "accepted"),
        masked=sum(1 for m in metas if m.judge_status == "masked"),
        rejected=sum(1 for m in metas if m.judge_status == "rejected"),
        patch_candidates=patch,
        test_candidates=tests,
        fix_candidates=fixes,
        best_candidate=judge.get("best_candidate", ""),
        warnings=judge.get("warnings", []) or [],
    )
