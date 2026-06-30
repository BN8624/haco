# postflight: report/packet 생성, HACO Validation 파싱, 누락 warning, 실패 fix 후보.
from haco.model_client import MockProvider
from haco.postflight import parse_haco_validation, run_postflight
from haco.preflight import run_preflight
from haco.utils import read_json


def _preflight(project, config):
    return run_preflight(project_path=project, task="Add subtract function",
                         profile="standard", config=config, provider=MockProvider())


def test_parse_validation_section():
    text = ("# result\n\n## HACO Validation\n\n"
            "task_packet_read: yes\naccepted_candidates_checked: yes\n"
            "candidate_usefulness: usable\nbounded_exploration_needed: no\n"
            "reason: worked well\n")
    v, missing = parse_haco_validation(text)
    assert missing is False
    assert v.task_packet_read is True
    assert v.candidate_usefulness == "usable"
    assert v.bounded_exploration_needed is False


def test_missing_validation_flagged():
    v, missing = parse_haco_validation("no section here")
    assert missing is True
    assert v is None


def test_postflight_outputs(sample_project, config):
    result = _preflight(sample_project, config)
    run = result["run_path"]
    from pathlib import Path
    (Path(run) / "execution_result.md").write_text(
        "## HACO Validation\n\ntask_packet_read: yes\n"
        "accepted_candidates_checked: yes\ncandidate_usefulness: usable\n"
        "bounded_exploration_needed: no\nreason: ok\n", encoding="utf-8")
    (Path(run) / "test_log.txt").write_text("1 passed", encoding="utf-8")
    pf = run_postflight(run_path=run, project_path=sample_project,
                        config=config, provider=MockProvider())
    assert (Path(run) / "report.md").exists()
    assert (Path(run) / "postflight_packet.json").exists()
    packet = read_json(Path(run) / "postflight_packet.json")
    assert packet["haco_validation"]["task_packet_read"] is True
    assert packet["main_agent_did_not_record_haco_validation"] is False


def test_postflight_without_test_log(sample_project, config):
    result = _preflight(sample_project, config)
    run = result["run_path"]
    from pathlib import Path
    (Path(run) / "execution_result.md").write_text("done, no validation",
                                                    encoding="utf-8")
    pf = run_postflight(run_path=run, project_path=sample_project,
                        config=config, provider=MockProvider())
    packet = read_json(Path(run) / "postflight_packet.json")
    assert packet["main_agent_did_not_record_haco_validation"] is True


def test_postflight_failure_generates_fix(sample_project, config):
    result = _preflight(sample_project, config)
    run = result["run_path"]
    from pathlib import Path
    (Path(run) / "execution_result.md").write_text(
        "## HACO Validation\ntask_packet_read: yes\n", encoding="utf-8")
    (Path(run) / "test_log.txt").write_text(
        "FAILED tests/test_calc.py::test_add - AssertionError", encoding="utf-8")
    pf = run_postflight(run_path=run, project_path=sample_project,
                        config=config, provider=MockProvider())
    assert pf["fix_candidates"]
    assert (Path(run) / "candidates" / "candidate_fix_01").exists()
