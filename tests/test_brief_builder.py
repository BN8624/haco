# brief_builder: mandatory first step, validation, accepted only, postflight 지시.
from haco.brief_builder import build_execution_brief, build_postflight_command
from haco.run_store import create_run
from haco.schemas import CandidateMetadata, TaskPacket


def test_postflight_command_defaults_on_empty():
    # 빈 인자는 기본값으로 채워 빈 자리(--run  --project )가 생기지 않는다.
    cmd = build_postflight_command("", "")
    assert cmd == "python -m haco postflight --run .haco/runs/latest --project ."
    assert build_postflight_command(None, None) == cmd
    assert "--run  " not in cmd


def test_brief_postflight_command_is_complete(tmp_path):
    run = create_run(tmp_path)
    packet = TaskPacket(run_id="r1", project_path="")
    brief = build_execution_brief(packet, [], run)
    assert "python -m haco postflight --run .haco/runs/latest --project ." in brief
    assert "--run  --project " not in brief
    assert "<this_run_dir>" not in brief


def _meta(cid, status):
    return CandidateMetadata(candidate_id=cid, kind="patch",
                             target_files=["pkg/calc.py"], judge_status=status,
                             expose_in_execution_brief=(status == "accepted"),
                             summary=f"summary {cid}")


def test_brief_contains_mandatory_and_validation(tmp_path):
    run = create_run(tmp_path)
    packet = TaskPacket(run_id="r1", project_path="/x")
    brief = build_execution_brief(packet, [], run)
    assert "Mandatory first step" in brief
    assert "HACO Validation" in brief
    assert "task_packet_read:" in brief
    assert "postflight" in brief
    assert "Bounded exploration" in brief
    assert "optional.diff" in brief


def test_brief_shows_accepted_only(tmp_path):
    run = create_run(tmp_path)
    packet = TaskPacket(run_id="r1", project_path="/x")
    metas = [_meta("candidate_01", "accepted"),
             _meta("candidate_02", "masked"),
             _meta("candidate_03", "rejected")]
    brief = build_execution_brief(packet, metas, run)
    assert "candidate_01" in brief
    assert "candidate_02" not in brief  # masked는 수만 표시
    assert "candidate_03" not in brief  # rejected 미노출
    assert "1 additional candidates exist but were masked" in brief


def test_skip_brief_warns(tmp_path):
    run = create_run(tmp_path)
    packet = TaskPacket(run_id="r1", project_path="/x",
                        haco_status="skip_to_main_agent", skip_reason="locator_failed")
    brief = build_execution_brief(packet, [], run)
    assert "Do not rely on candidates" in brief
    assert "bounded exploration" in brief.lower()
