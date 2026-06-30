# metrics.json 생성. HACO가 context bloat 원인이 되는지 추적한다.
from __future__ import annotations

from pathlib import Path

from haco.budget import char_count
from haco.utils import read_text


def build_metrics(*, input_text: str, snapshot: dict, task_packet: dict,
                  execution_brief: str, run_path: Path, provider: str,
                  worker_timings: dict[str, float], wall_time: float) -> dict:
    repo_map = snapshot.get("repo_map", [])
    candidates_dir = Path(run_path) / "candidates"
    candidate_chars = 0
    if candidates_dir.exists():
        for p in candidates_dir.rglob("*"):
            if p.is_file():
                candidate_chars += len(read_text(p))

    worker_out_dir = Path(run_path) / "worker_outputs"
    worker_output_chars = 0
    worker_count = 0
    if worker_out_dir.exists():
        for p in worker_out_dir.glob("*.json"):
            if p.name.endswith(".error.json"):
                continue
            worker_output_chars += len(read_text(p))
            worker_count += 1

    cs = task_packet.get("candidate_summary", {})
    return {
        "input_chars": len(input_text),
        "project_snapshot_chars": char_count(snapshot),
        "repo_map_chars": char_count(repo_map),
        "worker_output_chars": worker_output_chars,
        "task_packet_chars": char_count(task_packet),
        "execution_brief_chars": len(execution_brief),
        "candidate_chars": candidate_chars,
        "worker_count": worker_count,
        "provider": provider,
        "haco_status": task_packet.get("haco_status", "ready"),
        "skip_reason": task_packet.get("skip_reason", ""),
        "locator_passes": task_packet.get("locator_passes", 1),
        "locator_rescan_applied": task_packet.get("locator_rescan_applied", False),
        "candidate_counts": {
            "generated": cs.get("generated", 0),
            "accepted": cs.get("accepted", 0),
            "masked": cs.get("masked", 0),
            "rejected": cs.get("rejected", 0),
        },
        "candidate_usefulness": "unknown",
        "bounded_exploration_needed": False,
        "execution_validation_expected": True,
        "worker_timings": {k: round(v, 4) for k, v in worker_timings.items()},
        "preflight_wall_time_seconds": round(wall_time, 4),
        "compression_notes": snapshot.get("truncation_notes", []),
    }
