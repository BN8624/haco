# preflight: mock provider end-to-end 산출물 생성과 profile.
import json

from haco.model_client import MockProvider
from haco.preflight import run_preflight


def _run(project, task, config, profile="standard"):
    return run_preflight(project_path=project, task=task, profile=profile,
                         config=config, provider=MockProvider())


def test_preflight_creates_all_outputs(sample_project, config):
    result = _run(sample_project, "Add a subtract function to calc.py", config)
    run = result["run_path"]
    from pathlib import Path
    run = Path(run)
    assert (run / "input.md").exists()
    assert (run / "project_snapshot.json").exists()
    assert (run / "task_packet.json").exists()
    assert (run / "execution_brief.md").exists()
    assert (run / "metrics.json").exists()
    assert (run / "candidates").exists()
    wo = list((run / "worker_outputs").glob("*.json"))
    assert len(wo) >= 5


def test_snapshot_has_required_fields(sample_project, config):
    result = _run(sample_project, "task", config)
    from pathlib import Path
    snap = json.loads((Path(result["run_path"]) / "project_snapshot.json").read_text(
        encoding="utf-8"))
    for field in ("primary_language", "project_type", "test_frameworks",
                  "repo_map", "repo_map_status"):
        assert field in snap


def test_candidate_directory_structure(sample_project, config):
    result = _run(sample_project, "Add a subtract function to calc.py", config)
    from pathlib import Path
    c1 = Path(result["run_path"]) / "candidates" / "candidate_01"
    assert (c1 / "candidate.json").exists()
    assert (c1 / "edit_plan.md").exists()


def test_metrics_has_worker_timings(sample_project, config):
    result = _run(sample_project, "Add subtract", config)
    from pathlib import Path
    m = json.loads((Path(result["run_path"]) / "metrics.json").read_text(
        encoding="utf-8"))
    assert "worker_timings" in m
    assert "task_router" in m["worker_timings"]
    assert m["provider"] == "mock"


def test_quick_profile_skips_candidates(sample_project, config):
    result = _run(sample_project, "Update README docs only", config, profile="quick")
    assert result["packet"]["candidate_summary"]["generated"] == 0


def test_latest_marker(sample_project, config):
    _run(sample_project, "task", config)
    latest = sample_project / ".haco" / "runs" / "latest"
    assert latest.exists()


def test_deterministic_outputs(sample_project, config):
    r1 = _run(sample_project, "Add subtract function", config)
    r2 = _run(sample_project, "Add subtract function", config)
    assert r1["packet"]["task_type"] == r2["packet"]["task_type"]
    assert r1["packet"]["files_to_read"] == r2["packet"]["files_to_read"]
