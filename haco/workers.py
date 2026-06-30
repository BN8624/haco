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


def run_worker(provider: ModelProvider, name: str, context: dict,
               run_path: Path, config: Config) -> tuple[dict, float, bool]:
    """worker 1개를 실행한다. 반환: (validated_output, elapsed_seconds, ok)."""
    prompt = build_prompt(name, context)
    out_dir = Path(run_path) / "worker_outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    start = time.perf_counter()
    ok = True
    try:
        raw = provider.generate_json(prompt, name)
        validated = validate_worker_output(name, raw).model_dump()
        # worker 출력에 워커가 넣은 보조 필드(_target_files 등) 보존
        for k, v in raw.items():
            if k.startswith("_") and k not in validated:
                validated[k] = v
    except Exception as e:  # noqa: BLE001 - worker 실패는 전체를 죽이지 않는다
        ok = False
        validated = _fallback_output(name, f"{type(e).__name__}: {e}")
        write_json(out_dir / f"{name}.error.json", {
            "worker": name,
            "error_type": type(e).__name__,
            "error_message": str(e)[:500],
            "key_value_logged": False,
        })
    elapsed = time.perf_counter() - start

    write_json(out_dir / f"{name}.json", validated)
    return validated, elapsed, ok


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
