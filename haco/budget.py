# Token/size circuit breaker. JSON/Markdown 구조를 깨지 않는 structural trimming.
from __future__ import annotations

import json
from typing import Any

from haco.utils import estimate_tokens


def char_count(data: Any) -> int:
    if isinstance(data, str):
        return len(data)
    return len(json.dumps(data, ensure_ascii=False))


def token_estimate(data: Any) -> int:
    return estimate_tokens(data if isinstance(data, str) else
                           json.dumps(data, ensure_ascii=False))


def _fallback_snapshot(snapshot: dict, note: str) -> dict:
    return {
        "project_path": snapshot.get("project_path", ""),
        "primary_language": snapshot.get("primary_language", "unknown"),
        "project_type": snapshot.get("project_type", "unknown"),
        "test_frameworks": snapshot.get("test_frameworks", [])[:5],
        "package_files": snapshot.get("package_files", [])[:5],
        "important_files": snapshot.get("important_files", [])[:10],
        "keyword_file_matches": snapshot.get("keyword_file_matches", [])[:10],
        "search_hints": snapshot.get("search_hints", [])[:10],
        "repo_map": [],
        "repo_map_status": "skipped",
        "repo_map_notes": [],
        "tree_preview": [],
        "file_paths_sample": snapshot.get("file_paths_sample", [])[:30],
        "git_status": "",
        "recent_files": [],
        "readme_preview": "",
        "truncation_applied": True,
        "truncation_notes": [note],
        "notes": snapshot.get("notes", []),
    }


def trim_repo_map(repo_map: list[dict], max_chars: int) -> tuple[list[dict], list[str]]:
    """repo_map을 구조 보존 방식으로 줄인다. 항목/심볼/docstring 순으로 축소."""
    notes: list[str] = []
    rm = [dict(item) for item in repo_map]

    def size() -> int:
        return char_count(rm)

    if size() <= max_chars:
        return rm, notes

    # 1) 각 파일의 docstring_preview 축약
    for item in rm:
        for sym in item.get("symbols", []):
            if isinstance(sym, dict) and sym.get("docstring_preview"):
                sym["docstring_preview"] = sym["docstring_preview"][:40]
    if size() <= max_chars:
        notes.append("repo_map docstrings truncated.")
        return rm, notes

    # 2) 각 파일 symbols 뒤쪽부터 제거 (최소 1개는 유지)
    while size() > max_chars and any(len(i.get("symbols", [])) > 1 for i in rm):
        for item in rm:
            syms = item.get("symbols", [])
            if len(syms) > 1:
                syms.pop()
        notes.append("repo_map symbols trimmed.")
        if size() <= max_chars:
            break

    # 3) 파일 항목 자체를 뒤에서 제거
    while size() > max_chars and len(rm) > 1:
        rm.pop()
        notes.append("repo_map files trimmed.")

    return rm, list(dict.fromkeys(notes))


def trim_snapshot(snapshot: dict, max_chars: int) -> dict:
    """project_snapshot을 budget 안으로 줄인다. 실패 시 fallback minimal snapshot."""
    snap = dict(snapshot)
    notes: list[str] = list(snap.get("truncation_notes", []))

    if char_count(snap) <= max_chars:
        return snap

    snap["truncation_applied"] = True

    # 순서대로 중요도 낮은 list 필드 축소
    reductions = [
        ("tree_preview", 60),
        ("file_paths_sample", 120),
        ("recent_files", 10),
        ("keyword_file_matches", 20),
        ("git_status", None),  # 문자열 축약
        ("readme_preview", None),
    ]
    for field, cap in reductions:
        if char_count(snap) <= max_chars:
            break
        val = snap.get(field)
        if isinstance(val, list) and cap is not None and len(val) > cap:
            snap[field] = val[:cap]
            notes.append(f"{field} trimmed to {cap} items.")
        elif isinstance(val, str) and val:
            snap[field] = val[:500]
            notes.append(f"{field} truncated.")

    # repo_map 구조 trimming
    if char_count(snap) > max_chars and snap.get("repo_map"):
        budget = max(1000, max_chars // 3)
        snap["repo_map"], rm_notes = trim_repo_map(snap["repo_map"], budget)
        notes.extend(rm_notes)

    # 더 공격적으로 파일/트리 축소
    if char_count(snap) > max_chars:
        snap["file_paths_sample"] = snap.get("file_paths_sample", [])[:40]
        snap["tree_preview"] = snap.get("tree_preview", [])[:20]
        notes.append("file_paths_sample and tree_preview reduced aggressively.")

    snap["truncation_notes"] = list(dict.fromkeys(notes))

    # 그래도 안 되면 fallback
    try:
        if char_count(snap) > max_chars:
            snap = _fallback_snapshot(
                snapshot, "Fallback minimal snapshot used because budget trimming was insufficient.")
        json.dumps(snap, ensure_ascii=False)  # serialization 검증
    except (TypeError, ValueError):
        snap = _fallback_snapshot(
            snapshot, "Fallback minimal snapshot used because budget trimming failed.")

    return snap


def trim_text(text: str, max_chars: int, note_label: str = "text") -> tuple[str, list[str]]:
    """markdown/text를 code fence를 깨지 않도록 보수적으로 줄인다."""
    if len(text) <= max_chars:
        return text, []
    # fence 균형을 위해 줄 단위로 자르고, 열린 fence가 있으면 닫는다
    lines = text.splitlines()
    out: list[str] = []
    total = 0
    for line in lines:
        if total + len(line) + 1 > max_chars:
            break
        out.append(line)
        total += len(line) + 1
    joined = "\n".join(out)
    if joined.count("```") % 2 == 1:
        joined += "\n```"
    joined += "\n\n<!-- HACO: content truncated by budget -->\n"
    return joined, [f"{note_label} truncated to budget."]
