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


def test_resolve_run_id_via_project(tmp_path):
    # run ID만 주고 project_path로 <project>/.haco/runs/<id>를 해석한다.
    run = create_run(tmp_path, run_id="2026-01-01_000000")
    resolved = resolve_run("2026-01-01_000000", project_path=tmp_path)
    assert resolved.resolve() == run.resolve()


def test_resolve_latest_via_project(tmp_path):
    # 'latest'를 project_path 기준으로 해석한다.
    run = create_run(tmp_path, run_id="2026-01-01_000000")
    resolved = resolve_run("latest", project_path=tmp_path)
    assert resolved.name == run.name or resolved.resolve() == run.resolve()


def test_resolve_run_unknown_returns_original(tmp_path):
    # 못 찾으면 원본을 그대로 반환해 호출부가 존재 여부로 실패를 판단한다.
    resolved = resolve_run("nope", project_path=tmp_path)
    assert not resolved.exists()
