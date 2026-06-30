# file_locator 2-pass focused rescan과 skip_to_main_agent.
from haco.model_client import MockProvider
from haco.preflight import run_preflight
from haco.workers import focused_rescan


def test_focused_rescan_within_snapshot():
    snapshot = {
        "file_paths_sample": ["src/auth/login.py", "src/util.py", "README.md"],
        "repo_map": [{"file": "src/auth/login.py",
                      "symbols": [{"kind": "function", "name": "login"}]}],
    }
    out = focused_rescan(snapshot, ["login", "auth"])
    assert "src/auth/login.py" in out


def test_empty_project_skips(empty_project, config):
    result = run_preflight(project_path=empty_project,
                           task="Fix the authentication bug in the login handler",
                           profile="standard", config=config, provider=MockProvider())
    assert result["haco_status"] == "skip_to_main_agent"
    assert result["packet"]["skip_reason"] in (
        "locator_failed", "provider_failure", "repo_map_missing")


def test_rescan_recorded_when_applied(sample_project, config):
    # 매치가 안 되는 키워드로 low confidence 유발 후 rescan 경로 확인
    result = run_preflight(project_path=sample_project,
                           task="Improve performance somewhere generic",
                           profile="standard", config=config, provider=MockProvider())
    packet = result["packet"]
    assert packet["locator_passes"] in (1, 2)
