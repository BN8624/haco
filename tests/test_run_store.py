# run_store: runs 디렉터리 생성과 latest 해석.
from haco.run_store import create_run, resolve_run


def test_create_run_makes_dirs(tmp_path):
    run = create_run(tmp_path)
    assert run.exists()
    assert (run / "worker_outputs").exists()
    assert (run / "candidates").exists()
    assert (tmp_path / ".haco" / "runs" / "latest").exists()


def test_resolve_latest(tmp_path):
    run = create_run(tmp_path)
    latest = tmp_path / ".haco" / "runs" / "latest"
    resolved = resolve_run(latest)
    assert resolved.name == run.name or resolved.resolve() == run.resolve()


def test_create_two_runs_unique(tmp_path):
    r1 = create_run(tmp_path, run_id="2026-01-01_000000")
    r2 = create_run(tmp_path, run_id="2026-01-01_000000")
    assert r1 != r2
