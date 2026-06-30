# HACO 설정 로더. 기본값 + 선택적 config.yaml + 환경변수를 병합한다.
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - yaml은 선택 의존성
    yaml = None

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None


DEFAULT_CONFIG: dict[str, Any] = {
    "provider": "mock",
    "google": {
        "model": "gemma-4-31b-it",
        "api_key_env": "GOOGLE_API_KEY",
        "api_key_envs": [f"GOOGLE_API_KEY_{i:02d}" for i in range(1, 12)],
    },
    "provider_retry": {
        "max_retries": 3,
        "initial_backoff_seconds": 1,
        "max_backoff_seconds": 20,
        "rotate_keys_on_429": True,
        "fail_worker_on_exhausted_retries": False,
    },
    "concurrency": {
        "recommended_concurrency": 4,
        "max_concurrency": 11,
        "bootstrap_concurrency": 4,
    },
    "runs_dir": ".haco/runs",
    "profiles": {
        "default": "standard",
        "quick": ["task_router", "context_compressor", "file_locator", "doc_reporter"],
        "standard": [
            "task_router", "context_compressor", "file_locator",
            "patch_candidate", "test_candidate", "doc_reporter", "candidate_judge",
        ],
        "deep": [
            "task_router", "context_compressor", "file_locator",
            "patch_candidate", "test_candidate", "doc_reporter", "candidate_judge",
        ],
    },
    "limits": {
        "max_worker_output_chars": 6000,
        "max_reason_chars": 800,
        "max_candidate_chars": 20000,
        "max_files_in_snapshot": 300,
        "max_file_preview_chars": 6000,
        "fail_on_invalid_json": False,
    },
    "budgets": {
        "max_project_snapshot_chars": 30000,
        "max_repo_map_chars": 12000,
        "max_execution_brief_chars": 16000,
        "max_task_packet_chars": 12000,
        "max_candidate_total_chars": 40000,
        "token_estimation": "char_div_4",
    },
    "scanner": {
        "include_tree_depth": 3,
        "include_git_status": True,
        "include_recent_files": True,
        "include_readme_preview": True,
        "include_repo_map": True,
        "respect_gitignore": True,
        "ignore_dirs": [
            ".git", ".haco", ".venv", "venv", "node_modules",
            "__pycache__", "dist", "build",
        ],
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class Config:
    """병합된 설정에 대한 가벼운 접근 래퍼."""

    def __init__(self, data: dict[str, Any]):
        self.data = data

    def get(self, *keys: str, default: Any = None) -> Any:
        cur: Any = self.data
        for k in keys:
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur

    @property
    def provider(self) -> str:
        return self.data.get("provider", "mock")

    @property
    def profiles(self) -> dict:
        return self.data.get("profiles", {})

    def profile_workers(self, name: str) -> list[str]:
        profiles = self.profiles
        if name in profiles and isinstance(profiles[name], list):
            return list(profiles[name])
        # 알 수 없는 profile은 standard로 폴백
        return list(profiles.get("standard", DEFAULT_CONFIG["profiles"]["standard"]))


def load_env(project_path: Path | None = None) -> None:
    """프로젝트와 현재 디렉터리의 .env를 로드한다 (있으면)."""
    if load_dotenv is None:
        return
    candidates = []
    if project_path:
        candidates.append(Path(project_path) / ".env")
    candidates.append(Path.cwd() / ".env")
    for c in candidates:
        if c.exists():
            load_dotenv(c, override=False)


def load_config(config_path: str | Path | None = None,
                project_path: Path | None = None) -> Config:
    data = DEFAULT_CONFIG
    path = None
    if config_path:
        path = Path(config_path)
    else:
        for cand in (Path.cwd() / "config.yaml", Path.cwd() / "haco.yaml"):
            if cand.exists():
                path = cand
                break
    if path and path.exists() and yaml is not None:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(loaded, dict):
            data = _deep_merge(DEFAULT_CONFIG, loaded)

    data = dict(data)
    # 환경변수 override
    env_provider = os.environ.get("HACO_PROVIDER")
    if env_provider:
        data["provider"] = env_provider
    return Config(data)
