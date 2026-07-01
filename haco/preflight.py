# preflight 오케스트레이션: scan -> budget -> workers(stage/profile) -> candidates -> aggregate -> brief.
from __future__ import annotations

import asyncio
import subprocess
import time
from pathlib import Path

from haco.aggregate import build_task_packet
from haco.brief_builder import build_execution_brief
from haco.budget import trim_snapshot, trim_text
from haco.candidate_store import (apply_hard_filter, build_candidate_summary,
                                  write_patch_candidate, write_test_candidate)
from haco.config import Config
from haco.confidence import evaluate_confidence
from haco.context_pack import build_context_pack
from haco.metrics import build_metrics
from haco.model_client import ModelProvider, get_provider
from haco.ranking import post_locator_rerank
from haco.run_store import create_run
from haco.scanner import scan_project
from haco.schemas import TaskPacket
from haco.workers import (CORE_WORKERS, compact_snapshot, focused_rescan,
                          run_worker, run_worker_async)
from haco.utils import estimate_tokens, write_json, write_text


def _locator_needs_rescan(locator: dict, task_type: str) -> bool:
    if locator.get("confidence") == "low":
        return True
    if not locator.get("files_to_read"):
        return True
    if not locator.get("files_to_edit") and task_type in (
            "code_change", "test_failure", "refactor"):
        return True
    return False


def _patch_test_suppressed(task_type: str, risk: str) -> bool:
    """task_router 판단으로 patch/test 후보 생성을 생략할지."""
    if task_type in ("docs_only", "planning", "research"):
        return True
    return False


def _prior_change_reference(project_path: Path, files_to_edit: list[str],
                            task_type: str, run_path: Path, max_chars: int) -> str:
    """편집 대상 파일을 마지막으로 바꾼 커밋 diff를 참조 파일로 쓰고 그 rel 경로를 반환한다.

    반복 증분 작업(예: marker chain)에서 "직전에 비슷한 변경이 어떻게 됐는지" 템플릿을
    제공한다. git/커밋 이력이 없거나 code 변경 작업이 아니면 빈 문자열(아무 것도 안 씀).
    결정적: 동일 repo 상태면 동일 출력. provider 비의존.
    """
    if task_type not in ("code_change", "refactor", "test_failure"):
        return ""
    if not files_to_edit:
        return ""
    target = files_to_edit[0]

    def _git(*args: str) -> tuple[int, str]:
        try:
            p = subprocess.run(["git", "-C", str(project_path), *args],
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=15)
            return p.returncode, p.stdout
        except Exception:
            return 1, ""

    rc, out = _git("log", "-1", "--format=%H%x1f%s", "--", target)
    if rc != 0 or not out.strip():
        return ""
    commit, _, subject = out.strip().partition("\x1f")
    rc, diff = _git("show", "--stat", "--patch", commit)
    if rc != 0 or not diff.strip():
        return ""

    truncated = ""
    if len(diff) > max_chars:
        diff = diff[:max_chars]
        truncated = "\n…(diff truncated by HACO budget)…\n"

    body = (
        "# Prior change reference\n\n"
        f"The most recent commit that modified `{target}` was below. "
        "This is how a similar change was made before — use it as a **template**, "
        "adapt it to this task, and do not blindly copy.\n\n"
        f"- commit: `{commit}`\n- subject: {subject}\n\n"
        "```diff\n" + diff + truncated + "\n```\n"
    )
    write_text(run_path / "prior_change_reference.md", body)
    return "prior_change_reference.md"


def run_preflight(*, project_path: Path, task: str, profile: str,
                  config: Config, provider: ModelProvider | None = None,
                  run_path: Path | None = None) -> dict:
    project_path = Path(project_path)
    provider = provider or get_provider(config)
    wall_start = time.perf_counter()

    if run_path is None:
        runs_dir = config.get("runs_dir", default=".haco/runs")
        run_path = create_run(project_path, runs_dir)
    run_path = Path(run_path)

    write_text(run_path / "input.md", f"# HACO Task Input\n\n{task}\n")

    profile_workers = set(config.profile_workers(profile))
    timings: dict[str, float] = {}
    outputs: dict[str, dict] = {}
    core_failed: list[str] = []

    # ---- Stage 0: scan + budget ----
    snapshot_ok = True
    try:
        snapshot = scan_project(project_path, task, config)
    except Exception as e:  # noqa: BLE001
        snapshot_ok = False
        snapshot = {
            "project_path": str(project_path), "primary_language": "unknown",
            "project_type": "unknown", "test_frameworks": [], "repo_map": [],
            "repo_map_status": "skipped", "file_paths_sample": [],
            "truncation_applied": True,
            "truncation_notes": [f"scan failed: {type(e).__name__}"],
        }
    max_snap = config.get("budgets", "max_project_snapshot_chars", default=30000)
    snapshot = trim_snapshot(snapshot, max_snap)
    write_json(run_path / "project_snapshot.json", snapshot)

    ctx_snapshot = compact_snapshot(snapshot)

    def call(name: str, extra_ctx: dict | None = None) -> dict:
        context = {"task": task, "worker": name, "snapshot": ctx_snapshot,
                   "prior": outputs}
        if extra_ctx:
            context.update(extra_ctx)
        out, elapsed, ok = run_worker(provider, name, context, run_path, config)
        timings[name] = elapsed
        if not ok and name in CORE_WORKERS:
            core_failed.append(name)
        outputs[name] = out
        return out

    # ---- Stage 1: core workers (sequential) ----
    router = call("task_router")
    task_type = router.get("task_type", "unknown")
    risk = router.get("risk", "medium")

    call("context_compressor")
    locator = call("file_locator")

    # ---- Stage 1.5: focused rescan ----
    locator_passes = 1
    rescan_applied = False
    rescan_notes: list[str] = []
    if not core_failed and _locator_needs_rescan(locator, task_type):
        rescan = focused_rescan(snapshot, locator.get("search_keywords", []))
        if rescan:
            locator = call("file_locator", {"rescan_candidates": rescan})
            locator_passes = 2
            rescan_applied = True
            rescan_notes.append(
                "First pass had low confidence; retried with search_keywords "
                "against repo_map and file_paths_sample.")

    # ---- Stage 1.6: deterministic post-locator rerank ----
    # LLM locator 는 제안자. 여기서 결정론 content-aware 랭커가 최종 파일 순서를 확정한다.
    # rescan 이후(최종 locator)에 반드시 적용해 context_pack 이 올바른 파일을 excerpt 하게 한다.
    locator = post_locator_rerank(locator, snapshot, config)
    outputs["file_locator"] = locator  # aggregate/context_pack 이 이 보정본을 쓰게 반영
    locator_adjusted = bool(locator.get("locator_adjusted"))
    locator_adjust_reason = locator.get("locator_adjust_reason", "")

    # ---- skip 판단 ----
    skip = False
    skip_reason = ""
    suggested = ""
    if not snapshot_ok:
        skip, skip_reason = True, "repo_map_missing"
        suggested = "Improve scanner robustness for this project type."
    elif core_failed:
        skip, skip_reason = True, "provider_failure"
        suggested = "A core worker failed; check provider/JSON handling."
    elif locator.get("confidence") == "low" and not locator.get("files_to_read"):
        skip, skip_reason = True, "locator_failed"
        suggested = "Improve repo_map or search_hints for this project type."

    # ---- context pack + fail-closed 판정 (§9, §17.1; 후보 생성 前) ----
    # LLM이 보고한 locator confidence가 아니라 결정론 신호로 tier를 정한다.
    prelim = TaskPacket(
        files_to_read=locator.get("files_to_read", []) or [],
        files_to_edit=locator.get("files_to_edit", []) or [],
        search_keywords=locator.get("search_keywords", []) or [],
        haco_status="skip_to_main_agent" if skip else "ready")
    _prelim_md, prelim_cp_json = build_context_pack(
        project_path=project_path, snapshot=snapshot, packet=prelim, config=config)
    confidence = evaluate_confidence(
        snapshot=snapshot, locator=locator, context_pack_json=prelim_cp_json,
        task_type=task_type, config=config)
    if confidence["fail_closed_triggered"] and not skip:
        skip = True
        skip_reason = confidence["fail_closed_reason"] or "low_confidence"
        suggested = ("Fail-closed: deterministic confidence too low "
                     f"({', '.join(confidence['hard_gates_triggered']) or 'low_score'}); "
                     "main agent should use bounded exploration.")

    # ---- Stage 2: non-core 후보 생성 (concurrency 적용) ----
    # core worker(위)는 순차 유지. 여기서만 asyncio로 병렬화한다.
    metas = []
    suppressed = _patch_test_suppressed(task_type, risk)
    run_patch = (not skip and not suppressed and
                 "patch_candidate" in profile_workers and
                 task_type in ("code_change", "refactor", "test_failure"))
    run_test = (not skip and not suppressed and
                "test_candidate" in profile_workers)
    # fail-closed/skip이면 doc_reporter도 끈다(저신뢰 출력은 짧아야 함, §17.1).
    # 단 docs_only 작업은 문서 안내가 핵심이라 예외로 허용.
    run_doc = ((not skip or task_type == "docs_only") and
               "doc_reporter" in profile_workers)

    def acall_ctx(name: str, extra: dict | None = None) -> dict:
        c = {"task": task, "worker": name, "snapshot": ctx_snapshot, "prior": outputs}
        if extra:
            c.update(extra)
        return c

    async def _run_stage2() -> None:
        # Phase A (병렬): 서로 독립인 patch 후보(들) + doc_reporter.
        #   - deep profile은 patch 후보 복수를 asyncio.gather로 병렬 생성한다.
        #   - doc_reporter는 후보 생성과 병렬로 실행한다.
        specs: list[tuple] = []
        if run_patch:
            n_patch = 2 if profile == "deep" else 1
            for i in range(1, n_patch + 1):
                cid = f"candidate_{i:02d}"
                oname = "patch_candidate" if i == 1 else f"patch_candidate_{i:02d}"
                specs.append(("patch_candidate", {"candidate_id": cid}, oname,
                              ("patch", cid)))
        if run_doc:
            specs.append(("doc_reporter", {}, "doc_reporter", ("doc", None)))

        if specs:
            coros = [run_worker_async(provider, n, acall_ctx(n, ex), run_path,
                                      config, output_name=on)
                     for (n, ex, on, _tag) in specs]
            results = await asyncio.gather(*coros)
            # 완료 순서와 무관하게 spec 순서대로 결정적으로 반영한다.
            for (n, ex, on, tag), (out, elapsed, ok) in zip(specs, results):
                timings[on] = elapsed
                if tag[0] == "patch":
                    cid = tag[1]
                    out.setdefault("candidate_id", cid)
                    if cid == "candidate_01":
                        outputs["patch_candidate"] = out
                    metas.append(write_patch_candidate(run_path, out))
                else:
                    outputs["doc_reporter"] = out

        # Phase B (순차): test_candidate는 patch_candidate 이후 실행한다.
        if run_test:
            out, elapsed, _ok = await run_worker_async(
                provider, "test_candidate", acall_ctx("test_candidate"),
                run_path, config)
            timings["test_candidate"] = elapsed
            outputs["test_candidate"] = out
            meta = write_test_candidate(run_path, out, "candidate_test_01")
            if meta:
                metas.append(meta)

    asyncio.run(_run_stage2())

    # ---- Stage 3: judge + hard filter ----
    judge: dict = {}
    if not skip and metas and "candidate_judge" in profile_workers:
        judge = call("candidate_judge", {
            "candidates": [m.model_dump() for m in metas]})
    elif metas:
        # judge 없는 profile(quick엔 candidate 없음)에서는 기본 수용
        judge = {"accepted_candidates": [m.candidate_id for m in metas],
                 "best_candidate": metas[0].candidate_id if metas else ""}

    metas = apply_hard_filter(run_path, metas, judge, snapshot,
                              confidence_tier=confidence["confidence_tier"],
                              project_path=project_path)
    candidate_summary = build_candidate_summary(metas, judge)

    # ---- prior change reference (git 기반, 반복 증분 템플릿) ----
    prior_ref = ""
    if not skip:
        max_ref = config.get("budgets", "max_candidate_total_chars", default=40000)
        prior_ref = _prior_change_reference(
            project_path, locator.get("files_to_edit", []) or [],
            task_type, run_path, max_ref)

    # ---- context_pack (결정론적 focused excerpt; §9 최우선 산출물) ----
    # 최종 skip 상태를 반영해 만든다: fail-closed면 haco_status=skip이라 짧은 pack(§17.1).
    final_status_packet = TaskPacket(
        files_to_read=locator.get("files_to_read", []) or [],
        files_to_edit=locator.get("files_to_edit", []) or [],
        search_keywords=locator.get("search_keywords", []) or [],
        haco_status="skip_to_main_agent" if skip else "ready")
    cp_md, cp_json = build_context_pack(
        project_path=project_path, snapshot=snapshot, packet=final_status_packet,
        config=config)
    max_cp_tokens = config.get("budgets", "max_context_pack_tokens", default=8000)
    cp_md, cp_notes = trim_text(cp_md, max_cp_tokens * 4, "context_pack")
    # metric은 최종 context_pack 기준. fail-closed면 files=[]라 generated=False로 확정.
    cp_generated = (not skip) and bool(cp_json.get("files"))
    cp_tokens = cp_json.get("budget", {}).get("token_estimate", 0)

    # ---- aggregate ----
    packet = build_task_packet(
        run_id=run_path.name, project_path=str(project_path), outputs=outputs,
        core_failed=core_failed, skip=skip, skip_reason=skip_reason,
        locator_passes=locator_passes, locator_rescan_applied=rescan_applied,
        locator_rescan_notes=rescan_notes, candidate_summary=candidate_summary,
        locator_adjusted=locator_adjusted, locator_adjust_reason=locator_adjust_reason,
        suggested_improvement=suggested, prior_change_reference=prior_ref,
        confidence=confidence,
        context_pack_generated=cp_generated,
        context_pack_tokens_estimate=cp_tokens,
    )
    write_json(run_path / "task_packet.json", packet.model_dump())
    write_text(run_path / "context_pack.md", cp_md)
    write_json(run_path / "context_pack.json", cp_json)

    # ---- execution_brief ----
    brief = build_execution_brief(packet, metas, run_path)
    max_brief = config.get("budgets", "max_execution_brief_chars", default=16000)
    brief, brief_notes = trim_text(brief, max_brief, "execution_brief")
    write_text(run_path / "execution_brief.md", brief)

    # ---- metrics ----
    wall = time.perf_counter() - wall_start
    metrics = build_metrics(
        input_text=task, snapshot=snapshot, task_packet=packet.model_dump(),
        execution_brief=brief, run_path=run_path, provider=provider.name,
        worker_timings=timings, wall_time=wall,
    )
    metrics["context_pack_chars"] = len(cp_md)
    metrics["context_pack_tokens_estimate"] = estimate_tokens(cp_md)
    metrics["context_pack_files"] = len(cp_json.get("files", []))
    metrics["confidence_tier"] = confidence["confidence_tier"]
    metrics["evidence_score"] = confidence["evidence_score"]
    metrics["deterministic_signal_count"] = confidence["deterministic_signal_count"]
    metrics["fail_closed_triggered"] = confidence["fail_closed_triggered"]
    metrics["hard_gates_triggered"] = confidence["hard_gates_triggered"]
    metrics["locator_adjusted"] = locator_adjusted
    metrics["locator_adjust_reason"] = locator_adjust_reason
    if brief_notes or cp_notes:
        metrics["compression_notes"] = list(metrics["compression_notes"]) + brief_notes + cp_notes
    write_json(run_path / "metrics.json", metrics)

    return {
        "run_path": str(run_path),
        "task_packet": str(run_path / "task_packet.json"),
        "context_pack": str(run_path / "context_pack.md"),
        "execution_brief": str(run_path / "execution_brief.md"),
        "candidates": str(run_path / "candidates"),
        "metrics": str(run_path / "metrics.json"),
        "haco_status": packet.haco_status,
        "packet": packet.model_dump(),
    }
