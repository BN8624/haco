# §17 동시성: non-core 후보 생성 async 경로, core 순차 유지, timings 기록.
import asyncio
import json
from pathlib import Path

from haco.model_client import MockProvider
from haco.preflight import run_preflight
from haco.run_store import create_run
from haco.workers import build_prompt, run_worker_async


def test_mock_async_matches_sync():
    mp = MockProvider()
    prompt = build_prompt("task_router", {"task": "Add subtract", "snapshot": {},
                                          "prior": {}})
    sync = mp.generate_json(prompt, "task_router")
    asy = asyncio.run(mp.generate_json_async(prompt, "task_router"))
    assert sync == asy  # async 경로가 동일 결과(결정적)


def test_run_worker_async_mock(tmp_path, config):
    run = create_run(tmp_path)
    ctx = {"task": "Add subtract", "worker": "task_router", "snapshot": {},
           "prior": {}}
    out, elapsed, ok = asyncio.run(
        run_worker_async(MockProvider(), "task_router", ctx, run, config))
    assert ok is True
    assert out["worker"] == "task_router"
    assert (run / "worker_outputs" / "task_router.json").exists()
    assert isinstance(elapsed, float)


def test_deep_parallel_patch_candidates(sample_project, config):
    res = run_preflight(project_path=sample_project,
                        task="Add subtract and divide functions to calc.py",
                        profile="deep", config=config, provider=MockProvider())
    run = Path(res["run_path"])
    # deep은 복수 patch 후보를 async path로 생성 (결정적 순서)
    assert res["packet"]["candidate_summary"]["patch_candidates"] == [
        "candidate_01", "candidate_02"]
    assert (run / "candidates" / "candidate_01").exists()
    assert (run / "candidates" / "candidate_02").exists()
    # 분리된 worker_outputs 파일명 (덮어쓰기 없이 결정적)
    assert (run / "worker_outputs" / "patch_candidate.json").exists()
    assert (run / "worker_outputs" / "patch_candidate_02.json").exists()


def test_standard_single_patch_via_async(sample_project, config):
    res = run_preflight(project_path=sample_project,
                        task="Add a subtract function to calc.py",
                        profile="standard", config=config, provider=MockProvider())
    run = Path(res["run_path"])
    assert (run / "worker_outputs" / "patch_candidate.json").exists()
    assert not (run / "worker_outputs" / "patch_candidate_02.json").exists()


def test_core_runs_before_candidates(sample_project, config):
    # patch 후보의 target_files가 file_locator 결과와 일치 → core가 후보보다 먼저 완료됨을 의미
    res = run_preflight(project_path=sample_project,
                        task="Add a subtract function to calc.py",
                        profile="standard", config=config, provider=MockProvider())
    run = Path(res["run_path"])
    locator = json.loads(
        (run / "worker_outputs" / "file_locator.json").read_text(encoding="utf-8"))
    cand = json.loads(
        (run / "candidates" / "candidate_01" / "candidate.json").read_text(
            encoding="utf-8"))
    assert cand["target_files"]  # 비어있지 않음
    expected = locator.get("files_to_edit") or locator.get("files_to_read")
    assert cand["target_files"] == expected


def test_timings_and_wall_time_recorded(sample_project, config):
    res = run_preflight(project_path=sample_project,
                        task="Add subtract and divide functions",
                        profile="deep", config=config, provider=MockProvider())
    m = json.loads((Path(res["run_path"]) / "metrics.json").read_text(
        encoding="utf-8"))
    wt = m["worker_timings"]
    # core(순차) + non-core(async) 모두 timings 기록
    assert "task_router" in wt
    assert "file_locator" in wt
    assert "patch_candidate" in wt
    assert "patch_candidate_02" in wt
    assert "test_candidate" in wt
    assert m["preflight_wall_time_seconds"] >= 0.0


def test_deep_deterministic(sample_project, config):
    r1 = run_preflight(project_path=sample_project, task="Add subtract function",
                       profile="deep", config=config, provider=MockProvider())
    r2 = run_preflight(project_path=sample_project, task="Add subtract function",
                       profile="deep", config=config, provider=MockProvider())
    assert (r1["packet"]["candidate_summary"]["patch_candidates"] ==
            r2["packet"]["candidate_summary"]["patch_candidates"])
