# preflight 오케스트레이션: scan -> budget -> workers(stage/profile) -> candidates -> aggregate -> brief.
from __future__ import annotations

import time
from pathlib import Path

from haco.aggregate import build_task_packet
from haco.brief_builder import build_execution_brief
from haco.budget import trim_snapshot, trim_text
from haco.candidate_store import (apply_hard_filter, build_candidate_summary,
                                  write_patch_candidate, write_test_candidate)
from haco.config import Config
from haco.metrics import build_metrics
from haco.model_client import ModelProvider, get_provider
from haco.run_store import create_run
from haco.scanner import scan_project
from haco.schemas import TaskPacket
from haco.workers import (CORE_WORKERS, compact_snapshot, focused_rescan,
                          run_worker)
from haco.utils import write_json, write_text


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

    # ---- Stage 2: candidate generation (conditional) ----
    metas = []
    suppressed = _patch_test_suppressed(task_type, risk)
    run_patch = (not skip and not suppressed and
                 "patch_candidate" in profile_workers and
                 task_type in ("code_change", "refactor", "test_failure"))
    run_test = (not skip and not suppressed and
                "test_candidate" in profile_workers)

    if run_patch:
        # deep profile은 patch 후보 복수 생성
        n_patch = 2 if profile == "deep" else 1
        for i in range(1, n_patch + 1):
            cid = f"candidate_{i:02d}"
            out = call("patch_candidate", {"candidate_id": cid})
            out.setdefault("candidate_id", cid)
            metas.append(write_patch_candidate(run_path, out))

    if run_test:
        out = call("test_candidate")
        test_cid = "candidate_test_01"
        meta = write_test_candidate(run_path, out, test_cid)
        if meta:
            metas.append(meta)

    # doc_reporter (profile에 있으면 항상)
    if "doc_reporter" in profile_workers:
        call("doc_reporter")

    # ---- Stage 3: judge + hard filter ----
    judge: dict = {}
    if not skip and metas and "candidate_judge" in profile_workers:
        judge = call("candidate_judge", {
            "candidates": [m.model_dump() for m in metas]})
    elif metas:
        # judge 없는 profile(quick엔 candidate 없음)에서는 기본 수용
        judge = {"accepted_candidates": [m.candidate_id for m in metas],
                 "best_candidate": metas[0].candidate_id if metas else ""}

    metas = apply_hard_filter(run_path, metas, judge, snapshot)
    candidate_summary = build_candidate_summary(metas, judge)

    # ---- aggregate ----
    packet = build_task_packet(
        run_id=run_path.name, project_path=str(project_path), outputs=outputs,
        core_failed=core_failed, skip=skip, skip_reason=skip_reason,
        locator_passes=locator_passes, locator_rescan_applied=rescan_applied,
        locator_rescan_notes=rescan_notes, candidate_summary=candidate_summary,
        suggested_improvement=suggested,
    )
    write_json(run_path / "task_packet.json", packet.model_dump())

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
    if brief_notes:
        metrics["compression_notes"] = list(metrics["compression_notes"]) + brief_notes
    write_json(run_path / "metrics.json", metrics)

    return {
        "run_path": str(run_path),
        "task_packet": str(run_path / "task_packet.json"),
        "execution_brief": str(run_path / "execution_brief.md"),
        "candidates": str(run_path / "candidates"),
        "metrics": str(run_path / "metrics.json"),
        "haco_status": packet.haco_status,
        "packet": packet.model_dump(),
    }
