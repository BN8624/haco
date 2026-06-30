# worker/packet/candidate 스키마 검증 테스트.
from haco.schemas import (CandidateMetadata, PostflightPacket, TaskPacket,
                          validate_worker_output)


def test_worker_output_defaults():
    out = validate_worker_output("task_router", {"worker": "task_router"})
    assert out.task_type == "unknown"
    assert out.risk == "medium"


def test_unknown_worker_falls_back_to_base():
    out = validate_worker_output("nope", {"worker": "nope", "x": 1})
    assert out.worker == "nope"


def test_task_packet_schema():
    p = TaskPacket(run_id="r1", project_path="/x")
    d = p.model_dump()
    assert d["haco_status"] == "ready"
    assert "candidate_summary" in d
    assert d["candidate_summary"]["generated"] == 0


def test_postflight_packet_schema():
    p = PostflightPacket()
    d = p.model_dump()
    assert "haco_validation" in d
    assert "haco_effectiveness" in d


def test_candidate_metadata_defaults():
    m = CandidateMetadata(candidate_id="candidate_01")
    assert m.requires_human_or_agent_review is True
    assert m.direct_apply_recommended is False
    assert m.expose_in_execution_brief is False
