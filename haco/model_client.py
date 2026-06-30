# 모델 provider 추상화: mock(결정적) + google(retry/backoff/key rotation 골격).
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any

from haco.config import Config
from haco.utils import decode_context_block, repair_and_parse_json


class ProviderError(Exception):
    pass


class ModelProvider:
    name = "base"

    def generate_json(self, prompt: str, schema_name: str) -> dict:
        raise NotImplementedError

    async def generate_json_async(self, prompt: str, schema_name: str) -> dict:
        # 기본은 동기 호출 래핑
        return self.generate_json(prompt, schema_name)


# ----------------------------- Mock -----------------------------

def _detect_task_type(task: str) -> str:
    t = task.lower()
    if any(w in t for w in ["test fail", "failing test", "테스트 실패", "traceback",
                            "assertionerror", "stack trace"]):
        return "test_failure"
    if any(w in t for w in ["refactor", "리팩터", "리팩토링"]):
        return "refactor"
    if any(w in t for w in ["plan", "design only", "설계만", "계획"]):
        return "planning"
    if any(w in t for w in ["research", "investigate", "조사"]):
        return "research"
    if any(w in t for w in ["doc", "readme", "문서", "주석", "comment only"]) and \
            not any(w in t for w in ["code", "function", "구현", "fix bug"]):
        return "docs_only"
    return "code_change"


def _detect_risk(task: str, task_type: str) -> str:
    t = task.lower()
    if any(w in t for w in ["delete", "drop", "rollback", "migrate", "rewrite",
                            "전체", "모두 삭제", "롤백", "마이그레이션"]):
        return "high"
    if task_type in ("docs_only", "planning", "research"):
        return "low"
    return "medium"


class MockProvider(ModelProvider):
    """API 키 없이 항상 동작하는 결정적 provider. 프롬프트의 컨텍스트 블록을 읽는다."""

    name = "mock"

    def generate_json(self, prompt: str, schema_name: str) -> dict:
        ctx = decode_context_block(prompt)
        task = ctx.get("task", "")
        snap = ctx.get("snapshot", {})
        prior = ctx.get("prior", {})

        handler = getattr(self, f"_mock_{schema_name}", None)
        if handler is None:
            # bootstrap reviewer 등 worker 스키마가 없는 호출용 기본 출력
            return {"worker": schema_name, "findings": [],
                    "reason": "mock review: no blocking issues found (deterministic stub)."}
        return handler(task, snap, prior, ctx)

    def _mock_task_router(self, task, snap, prior, ctx):
        tt = _detect_task_type(task)
        risk = _detect_risk(task, tt)
        mode = {
            "docs_only": "preflight_only",
            "planning": "preflight_only",
            "research": "preflight_only",
            "test_failure": "failure_fix",
            "refactor": "candidate_generation",
            "code_change": "candidate_generation",
        }.get(tt, "candidate_generation")
        return {
            "worker": "task_router",
            "task_type": tt,
            "user_decision_needed": False,
            "risk": risk,
            "recommended_mode": mode,
            "reason": f"Classified as {tt} with {risk} risk based on task wording.",
        }

    def _mock_context_compressor(self, task, snap, prior, ctx):
        compressed = task.strip().replace("\n", " ")
        if len(compressed) > 600:
            compressed = compressed[:600] + "…"
        lang = snap.get("primary_language", "unknown")
        return {
            "worker": "context_compressor",
            "compressed_context": compressed,
            "known_constraints": [f"primary_language={lang}"] if lang != "unknown" else [],
            "assumptions": ["Proceed with minimal, surgical changes."],
            "open_questions": [],
            "reason": "Compressed user task into a short actionable context.",
        }

    def _mock_file_locator(self, task, snap, prior, ctx):
        files = snap.get("files", []) or []
        kw_matches = snap.get("keyword_matches", []) or []
        repo_files = snap.get("repo_map_files", []) or []
        keywords = snap.get("search_hints", []) or []

        ranked = list(dict.fromkeys(kw_matches + repo_files))
        # focused rescan candidates가 전달되면 우선 사용
        rescan = ctx.get("rescan_candidates")
        if rescan:
            ranked = list(dict.fromkeys(rescan + ranked))

        files_to_read = ranked[:4]
        if not files_to_read and files:
            files_to_read = files[:3]

        editable = [f for f in files_to_read
                    if f.endswith((".py", ".js", ".ts", ".rs", ".go", ".tsx", ".jsx"))]
        files_to_edit = editable[:2]

        if files_to_read and (kw_matches or rescan):
            confidence = "medium"
        elif files_to_read:
            confidence = "low"
        else:
            confidence = "low"

        return {
            "worker": "file_locator",
            "files_to_read": files_to_read,
            "files_to_edit": files_to_edit,
            "search_keywords": keywords[:8],
            "confidence": confidence,
            "reason": "Selected files from keyword matches and repo_map; "
                      "kept edit list conservative.",
        }

    def _mock_patch_candidate(self, task, snap, prior, ctx):
        loc = prior.get("file_locator", {})
        targets = loc.get("files_to_edit") or loc.get("files_to_read") or []
        cid = ctx.get("candidate_id", "candidate_01")
        method = "search_replace" if targets else "strategy_only"
        return {
            "worker": "patch_candidate",
            "candidate_id": cid,
            "candidate_dir": f"candidates/{cid}",
            "preferred_apply_method": method,
            "summary": f"Proposed change for: {task.strip()[:120]}",
            "risk": prior.get("task_router", {}).get("risk", "medium"),
            "assumptions": [] if targets else ["Target file uncertain; strategy only."],
            "reason": "Generated a candidate package for the main agent to review.",
            "_target_files": targets,
            "_language": snap.get("primary_language", "unknown"),
        }

    def _mock_test_candidate(self, task, snap, prior, ctx):
        frameworks = snap.get("test_frameworks", []) or []
        lang = snap.get("primary_language", "unknown")
        if lang == "unknown" or not frameworks:
            scope = "smoke"
            tests = []
        else:
            scope = "focused"
            tests = frameworks
        return {
            "worker": "test_candidate",
            "test_scope": scope,
            "tests_to_run": tests,
            "test_candidate_paths": [],
            "reason": f"Test scope set to {scope} based on detected frameworks.",
            "_language": lang,
        }

    def _mock_failure_fixer(self, task, snap, prior, ctx):
        cid = ctx.get("candidate_id", "candidate_fix_01")
        return {
            "worker": "failure_fixer",
            "fix_candidate_id": cid,
            "likely_cause": "Most recent change likely broke an assertion or import.",
            "candidate_dir": f"candidates/{cid}",
            "tests_to_rerun": snap.get("test_frameworks", []) or [],
            "reason": "Proposed a fix candidate from the failure log.",
        }

    def _mock_doc_reporter(self, task, snap, prior, ctx):
        return {
            "worker": "doc_reporter",
            "new_doc_needed": False,
            "docs_to_update": [],
            "docs_to_avoid": ["Do not create new planning documents."],
            "report_draft": f"Task: {task.strip()[:160]}",
            "reason": "Documentation creation suppressed by default.",
        }

    def _mock_candidate_judge(self, task, snap, prior, ctx):
        candidates = ctx.get("candidates", []) or []
        accepted, masked, rejected = [], [], []
        for c in candidates:
            cid = c.get("candidate_id")
            has_target = bool(c.get("target_files"))
            method = c.get("preferred_apply_method", "strategy_only")
            if has_target or method == "strategy_only":
                accepted.append(cid)
            else:
                rejected.append(cid)
        best = accepted[0] if accepted else ""
        return {
            "worker": "candidate_judge",
            "accepted_candidates": accepted,
            "masked_candidates": masked,
            "rejected_candidates": rejected,
            "best_candidate": best,
            "warnings": [] if accepted else ["No high-confidence candidate."],
            "reason": "Accepted candidates with plausible targets or explicit strategy.",
        }


# ----------------------------- Google -----------------------------

class GoogleProvider(ModelProvider):
    """Gemini/Gemma 호출 골격. retry/backoff/key rotation 포함. 키 없으면 mock 폴백 불가 → 예외."""

    name = "google"

    def __init__(self, config: Config, sleep_func=time.sleep):
        self.config = config
        self.model = config.get("google", "model", default="gemma-4-31b-it")
        retry = config.get("provider_retry", default={})
        self.max_retries = retry.get("max_retries", 3)
        self.initial_backoff = retry.get("initial_backoff_seconds", 1)
        self.max_backoff = retry.get("max_backoff_seconds", 20)
        self.rotate_on_429 = retry.get("rotate_keys_on_429", True)
        self._sleep = sleep_func
        self.key_slots = self._discover_key_slots(config)
        self._key_index = 0

    @staticmethod
    def _discover_key_slots(config: Config) -> list[str]:
        """config의 키 목록 + 환경변수 패턴(_1.._11, _01.._11)을 모두 인식."""
        slots: list[str] = []
        configured = config.get("google", "api_key_envs", default=[]) or []
        for name in configured:
            if os.environ.get(name):
                slots.append(name)
        single = config.get("google", "api_key_env", default="GOOGLE_API_KEY")
        for name in (single, "GOOGLE_API_KEY", "HACO_GOOGLE_API_KEY"):
            if name and os.environ.get(name) and name not in slots:
                slots.append(name)
        # 정규식 스캔으로 _1.._N / _01.._N 모두 수집
        for env_name in os.environ:
            if re.fullmatch(r"GOOGLE_API_KEY_\d+", env_name) and env_name not in slots:
                slots.append(env_name)
        # 정렬: 숫자 기준
        def keynum(s: str) -> int:
            m = re.search(r"_(\d+)$", s)
            return int(m.group(1)) if m else 0
        slots.sort(key=keynum)
        return slots

    def current_key_slot(self) -> str:
        if not self.key_slots:
            return ""
        return self.key_slots[self._key_index % len(self.key_slots)]

    def _rotate_key(self) -> None:
        if self.key_slots:
            self._key_index = (self._key_index + 1) % len(self.key_slots)

    def _make_client(self, slot: str):
        from google import genai  # type: ignore
        return genai.Client(api_key=os.environ[slot])

    def generate_json(self, prompt: str, schema_name: str) -> dict:
        if not self.key_slots:
            raise ProviderError(
                "No Google API key found in environment. Set GOOGLE_API_KEY or "
                "GOOGLE_API_KEY_1..N, or use provider=mock.")
        backoff = self.initial_backoff
        last_err: Exception | None = None
        for attempt in range(self.max_retries + 1):
            slot = self.current_key_slot()
            try:
                client = self._make_client(slot)
                resp = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={"response_mime_type": "application/json"},
                )
                text = getattr(resp, "text", "") or ""
                return repair_and_parse_json(text)
            except Exception as e:  # noqa: BLE001 - provider 견고성 우선
                last_err = e
                msg = str(e).lower()
                transient = any(code in msg for code in
                                ["429", "rate", "500", "502", "503", "timeout",
                                 "deadline", "unavailable"])
                if attempt >= self.max_retries or not transient:
                    break
                if self.rotate_on_429 and ("429" in msg or "rate" in msg):
                    self._rotate_key()
                self._sleep(min(backoff, self.max_backoff))
                backoff = min(backoff * 2, self.max_backoff)
        raise ProviderError(
            f"Google provider failed for {schema_name} via slot "
            f"{self.current_key_slot()}: {type(last_err).__name__}")


def get_provider(config: Config, sleep_func=time.sleep) -> ModelProvider:
    provider = config.provider
    if provider == "google":
        return GoogleProvider(config, sleep_func=sleep_func)
    return MockProvider()
