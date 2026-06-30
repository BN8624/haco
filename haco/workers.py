# worker prompt 로더와 실행 primitive. validation, fallback, 2-pass focused rescan 포함.
from __future__ import annotations

import time
from pathlib import Path

from haco.config import Config
from haco.model_client import ModelProvider
from haco.schemas import validate_worker_output
from haco.utils import encode_context_block, write_json

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"

CORE_WORKERS = ("task_router", "context_compressor", "file_locator")


def load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"You are the HACO worker '{name}'. Respond ONLY with valid JSON."


def compact_snapshot(snapshot: dict) -> dict:
    """worker 컨텍스트에 넣을 작은 snapshot 요약."""
    repo_files = [item.get("file") for item in snapshot.get("repo_map", []) or []
                  if isinstance(item, dict) and item.get("file")]
    return {
        "primary_language": snapshot.get("primary_language", "unknown"),
        "project_type": snapshot.get("project_type", "unknown"),
        "test_frameworks": snapshot.get("test_frameworks", []),
        "files": snapshot.get("file_paths_sample", [])[:60],
        "repo_map_files": repo_files[:60],
        "keyword_matches": snapshot.get("keyword_file_matches", []),
        "search_hints": snapshot.get("search_hints", []),
    }


def build_prompt(name: str, context: dict) -> str:
    return load_prompt(name) + "\n\n" + encode_context_block(context)


def _fallback_output(name: str, reason: str) -> dict:
    base = validate_worker_output(name, {"worker": name}).model_dump()
    base["reason"] = f"fallback: {reason}"
    base["_haco_fallback"] = True
    return base


def _record_success(name: str, raw: dict, run_path: Path,
                    output_name: str | None) -> dict:
    out_dir = Path(run_path) / "worker_outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    validated = validate_worker_output(name, raw).model_dump()
    # worker 출력에 워커가 넣은 보조 필드(_target_files 등) 보존
    for k, v in raw.items():
        if k.startswith("_") and k not in validated:
            validated[k] = v
    write_json(out_dir / f"{output_name or name}.json", validated)
    return validated


def _record_failure(name: str, e: Exception, run_path: Path,
                    output_name: str | None) -> dict:
    out_dir = Path(run_path) / "worker_outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    validated = _fallback_output(name, f"{type(e).__name__}: {e}")
    write_json(out_dir / f"{name}.error.json", {
        "worker": name,
        "error_type": type(e).__name__,
        "error_message": str(e)[:500],
        "key_value_logged": False,
    })
    write_json(out_dir / f"{output_name or name}.json", validated)
    return validated


def run_worker(provider: ModelProvider, name: str, context: dict,
               run_path: Path, config: Config,
               output_name: str | None = None) -> tuple[dict, float, bool]:
    """worker 1개를 동기로 실행한다. 반환: (validated_output, elapsed_seconds, ok).

    output_name으로 worker_outputs 파일명을 분리할 수 있다(복수 patch 후보 등).
    """
    prompt = build_prompt(name, context)
    start = time.perf_counter()
    try:
        raw = provider.generate_json(prompt, name)
    except Exception as e:  # noqa: BLE001 - worker 실패는 전체를 죽이지 않는다
        elapsed = time.perf_counter() - start
        return _record_failure(name, e, run_path, output_name), elapsed, False
    elapsed = time.perf_counter() - start
    return _record_success(name, raw, run_path, output_name), elapsed, True


async def run_worker_async(provider: ModelProvider, name: str, context: dict,
                           run_path: Path, config: Config,
                           output_name: str | None = None) -> tuple[dict, float, bool]:
    """worker 1개를 비동기로 실행한다(generate_json_async 사용).

    동기 provider도 to_thread로 감싸지므로 asyncio.gather로 병렬화된다.
    결과 파일명은 output_name으로 결정적으로 분리한다.
    """
    prompt = build_prompt(name, context)
    start = time.perf_counter()
    try:
        raw = await provider.generate_json_async(prompt, name)
    except Exception as e:  # noqa: BLE001
        elapsed = time.perf_counter() - start
        return _record_failure(name, e, run_path, output_name), elapsed, False
    elapsed = time.perf_counter() - start
    return _record_success(name, raw, run_path, output_name), elapsed, True


def focused_rescan(snapshot: dict, search_keywords: list[str], top_n: int = 8) -> list[str]:
    """이미 수집한 snapshot/repo_map 안에서만 focused match 수행 (full scan 아님)."""
    if not search_keywords:
        return []
    kws = [k.lower() for k in search_keywords]
    candidates = list(snapshot.get("file_paths_sample", []) or [])
    repo_map = snapshot.get("repo_map", []) or []

    scored: list[tuple[int, str]] = []
    for path in candidates:
        low = path.lower()
        score = sum(1 for k in kws if k in low)
        if score:
            scored.append((score, path))

    # repo_map symbol/docstring 매칭
    for item in repo_map:
        if not isinstance(item, dict):
            continue
        f = item.get("file", "")
        text = (f + " " + str(item.get("symbols", ""))).lower()
        score = sum(1 for k in kws if k in text)
        if score and f:
            scored.append((score + 1, f))

    scored.sort(key=lambda x: (-x[0], x[1]))
    out: list[str] = []
    for _, path in scored:
        if path not in out:
            out.append(path)
        if len(out) >= top_n:
            break
    return out
