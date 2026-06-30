# 모든 worker 출력과 packet에 대한 pydantic 스키마. 관대한 검증(기본값/extra 허용).
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

TaskType = str  # docs_only | code_change | test_failure | refactor | planning | research | unknown
Risk = str      # low | medium | high
Confidence = str  # low | medium | high


class WorkerBase(BaseModel):
    model_config = {"extra": "allow"}
    worker: str = ""
    reason: str = ""


class TaskRouterOutput(WorkerBase):
    worker: str = "task_router"
    task_type: TaskType = "unknown"
    user_decision_needed: bool = False
    risk: Risk = "medium"
    recommended_mode: str = "candidate_generation"


class ContextCompressorOutput(WorkerBase):
    worker: str = "context_compressor"
    compressed_context: str = ""
    known_constraints: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class FileLocatorOutput(WorkerBase):
    worker: str = "file_locator"
    files_to_read: list[str] = Field(default_factory=list)
    files_to_edit: list[str] = Field(default_factory=list)
    search_keywords: list[str] = Field(default_factory=list)
    confidence: Confidence = "low"


class SearchReplaceEdit(BaseModel):
    model_config = {"extra": "allow"}
    file: str = ""
    operation: str = "replace"  # replace | insert_after_anchor | insert_before_anchor
    search: str = ""
    replace: str = ""
    notes: str = ""


class ReplacementBlock(BaseModel):
    model_config = {"extra": "allow"}
    file: str = ""
    target: str = ""
    language: str = "unknown"
    code: str = ""
    apply_method: str = "replace entire function"


class PatchCandidateOutput(WorkerBase):
    worker: str = "patch_candidate"
    candidate_id: str = "candidate_01"
    candidate_dir: str = "candidates/candidate_01"
    preferred_apply_method: str = "strategy_only"
    summary: str = ""
    risk: Risk = "medium"
    assumptions: list[str] = Field(default_factory=list)
    # 실제 Gemma 코드 후보 내용. 비어 있으면 candidate_store가 skeleton으로 폴백한다.
    edit_plan: str | None = None
    search_replace_edits: list[SearchReplaceEdit] = Field(default_factory=list)
    replacement_blocks: list[ReplacementBlock] = Field(default_factory=list)


class TestCandidateOutput(WorkerBase):
    worker: str = "test_candidate"
    test_scope: str = "unknown"
    tests_to_run: list[str] = Field(default_factory=list)
    test_candidate_paths: list[str] = Field(default_factory=list)


class FailureFixerOutput(WorkerBase):
    worker: str = "failure_fixer"
    fix_candidate_id: str = "candidate_fix_01"
    likely_cause: str = ""
    candidate_dir: str = "candidates/candidate_fix_01"
    tests_to_rerun: list[str] = Field(default_factory=list)


class DocReporterOutput(WorkerBase):
    worker: str = "doc_reporter"
    new_doc_needed: bool = False
    docs_to_update: list[str] = Field(default_factory=list)
    docs_to_avoid: list[str] = Field(default_factory=list)
    report_draft: str = ""


class CandidateJudgeOutput(WorkerBase):
    worker: str = "candidate_judge"
    accepted_candidates: list[str] = Field(default_factory=list)
    masked_candidates: list[str] = Field(default_factory=list)
    rejected_candidates: list[str] = Field(default_factory=list)
    best_candidate: str = ""
    warnings: list[str] = Field(default_factory=list)


class CandidateMetadata(BaseModel):
    model_config = {"extra": "allow"}
    candidate_id: str
    kind: str = "patch"  # patch | test | fix | doc | strategy
    target_files: list[str] = Field(default_factory=list)
    language: str = "unknown"
    confidence: Confidence = "low"
    requires_human_or_agent_review: bool = True
    direct_apply_recommended: bool = False
    preferred_apply_method: str = "strategy_only"
    judge_status: str = "masked"  # accepted | masked | rejected
    judge_reason: str = ""
    expose_in_execution_brief: bool = False
    summary: str = ""
    risk: Risk = "medium"
    reason: str = ""


class CandidateSummary(BaseModel):
    model_config = {"extra": "allow"}
    generated: int = 0
    accepted: int = 0
    masked: int = 0
    rejected: int = 0
    patch_candidates: list[str] = Field(default_factory=list)
    test_candidates: list[str] = Field(default_factory=list)
    fix_candidates: list[str] = Field(default_factory=list)
    best_candidate: str = ""
    warnings: list[str] = Field(default_factory=list)


class TaskPacket(BaseModel):
    model_config = {"extra": "allow"}
    run_id: str = ""
    project_path: str = ""
    haco_status: str = "ready"  # ready | skip_to_main_agent
    skip_reason: str = ""
    suggested_haco_improvement: str = ""
    locator_passes: int = 1
    locator_rescan_applied: bool = False
    locator_rescan_notes: list[str] = Field(default_factory=list)
    task_type: TaskType = "unknown"
    user_decision_needed: bool = False
    risk: Risk = "medium"
    recommended_mode: str = "candidate_generation"
    compressed_context: str = ""
    files_to_read: list[str] = Field(default_factory=list)
    files_to_edit: list[str] = Field(default_factory=list)
    search_keywords: list[str] = Field(default_factory=list)
    tests_to_run: list[str] = Field(default_factory=list)
    test_scope: str = "unknown"
    long_run_needed: bool = False
    docs_to_update: list[str] = Field(default_factory=list)
    new_doc_needed: bool = False
    candidate_summary: CandidateSummary = Field(default_factory=CandidateSummary)
    constraints: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    recommended_action: str = ""
    reason: str = ""
    worker_outputs: dict[str, str] = Field(default_factory=dict)


class HacoValidation(BaseModel):
    model_config = {"extra": "allow"}
    task_packet_read: bool = False
    accepted_candidates_checked: bool = False
    candidate_usefulness: str = "none"  # usable | partially_usable | unusable | none
    bounded_exploration_needed: bool = False
    reason: str = ""


class HacoEffectiveness(BaseModel):
    model_config = {"extra": "allow"}
    main_agent_used_haco: bool = False
    skip_to_main_agent: bool = False
    notes: str = ""


class PostflightPacket(BaseModel):
    model_config = {"extra": "allow"}
    run_id: str = ""
    project_path: str = ""
    task_type: str = "unknown"
    haco_status: str = "ready"
    skip_reason: str = ""
    suggested_haco_improvement: str = ""
    haco_validation: HacoValidation = Field(default_factory=HacoValidation)
    haco_effectiveness: HacoEffectiveness = Field(default_factory=HacoEffectiveness)
    main_agent_did_not_record_haco_validation: bool = False
    tests_ran: bool = False
    tests_passed: bool | None = None
    fix_candidates: list[str] = Field(default_factory=list)


WORKER_SCHEMAS: dict[str, type[WorkerBase]] = {
    "task_router": TaskRouterOutput,
    "context_compressor": ContextCompressorOutput,
    "file_locator": FileLocatorOutput,
    "patch_candidate": PatchCandidateOutput,
    "test_candidate": TestCandidateOutput,
    "failure_fixer": FailureFixerOutput,
    "doc_reporter": DocReporterOutput,
    "candidate_judge": CandidateJudgeOutput,
}


def validate_worker_output(worker: str, data: dict[str, Any]) -> WorkerBase:
    """worker 출력 dict를 해당 스키마로 검증한다. 알 수 없는 worker는 WorkerBase."""
    schema = WORKER_SCHEMAS.get(worker, WorkerBase)
    return schema.model_validate(data)
