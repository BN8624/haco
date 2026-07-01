# postflight: report/packet 생성, HACO Validation 파싱, 누락 warning, 실패 fix 후보.
import pytest

from haco.model_client import MockProvider
from haco.postflight import (_detect_test_outcome, parse_haco_validation,
                             run_postflight)
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
    assert (Path(run) / "auto_diff_summary.md").exists()  # §7.3 산출물
    assert pf["auto_diff_summary"].endswith("auto_diff_summary.md")
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


@pytest.mark.parametrize("log, expected", [
    ("===== 1 failed, 71 passed in 4.54s =====", False),  # 실제 pytest 실패 요약
    ("0 failed, 5 passed", True),                          # 명시적 0 failed
    ("72 passed in 4.54s", True),                          # 전부 통과
    ("===== 2 errors in 0.3s =====", False),               # collection error 요약
    ("FAILED tests/test_calc.py::test_add - AssertionError", False),  # 단일 라인(요약 없음)
    ("tests/test_error_handling.py::test_x passed\n5 passed in 1s", True),  # 테스트명 error 오탐 방지
    ("ran 5 tests in 0.1s\n\nok", True),                   # unittest 통과
    ("mode smoke ticks 5000 status PASS\nseeds 1 determinism_fail 0", True),  # 자체 verifier status PASS
    ("mode quick ticks 5000 status FAIL\ndeterminism_fail 3", False),         # 자체 verifier status FAIL
    ("status PASS\nstatus PASS", True),                    # 다중 status 전부 통과
    ("status PASS\nstatus FAIL", False),                   # 다중 status 중 하나 실패
])
def test_detect_test_outcome(tmp_path, log, expected):
    (tmp_path / "test_log.txt").write_text(log, encoding="utf-8")
    ran, passed = _detect_test_outcome(tmp_path)
    assert ran is True
    assert passed is expected


def test_detect_test_outcome_empty_is_unknown(tmp_path):
    (tmp_path / "test_log.txt").write_text("   \n", encoding="utf-8")
    ran, passed = _detect_test_outcome(tmp_path)
    assert ran is True and passed is None


def test_postflight_report_unknown_not_failed(sample_project, config):
    # tests_passed가 None(미상)이면 report는 'failed'가 아니라 'unknown'으로 표기해야 한다.
    result = _preflight(sample_project, config)
    run = result["run_path"]
    from pathlib import Path
    (Path(run) / "execution_result.md").write_text(
        "## HACO Validation\ntask_packet_read: yes\n", encoding="utf-8")
    (Path(run) / "test_log.txt").write_text(
        "some output with no recognizable test outcome", encoding="utf-8")
    run_postflight(run_path=run, project_path=sample_project,
                   config=config, provider=MockProvider())
    report = (Path(run) / "report.md").read_text(encoding="utf-8")
    assert "- Tests: unknown" in report
    assert "- Tests: failed" not in report


def test_postflight_verifier_status_pass_is_passed(sample_project, config):
    # 자체 verifier의 'status PASS' 라인을 통과로 인식하고 fix 후보를 만들지 않아야 한다.
    result = _preflight(sample_project, config)
    run = result["run_path"]
    from pathlib import Path
    (Path(run) / "execution_result.md").write_text(
        "## HACO Validation\ntask_packet_read: yes\n", encoding="utf-8")
    (Path(run) / "test_log.txt").write_text(
        "mode smoke ticks 5000 status PASS\nseeds 1 determinism_fail 0 forbidden 0",
        encoding="utf-8")
    pf = run_postflight(run_path=run, project_path=sample_project,
                        config=config, provider=MockProvider())
    report = (Path(run) / "report.md").read_text(encoding="utf-8")
    assert "- Tests: passed" in report
    assert not pf["fix_candidates"]


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


def test_postflight_pytest_summary_triggers_fix(sample_project, config):
    # 통과 테스트와 공존하는 실제 pytest 실패 요약도 fix 후보를 생성해야 한다(회귀 방지).
    result = _preflight(sample_project, config)
    run = result["run_path"]
    from pathlib import Path
    (Path(run) / "execution_result.md").write_text(
        "## HACO Validation\ntask_packet_read: yes\n", encoding="utf-8")
    (Path(run) / "test_log.txt").write_text(
        "===== 1 failed, 71 passed in 4.54s =====", encoding="utf-8")
    pf = run_postflight(run_path=run, project_path=sample_project,
                        config=config, provider=MockProvider())
    assert pf["fix_candidates"]
