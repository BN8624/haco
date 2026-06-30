# 공용 헬퍼: 시간 ID, JSON 파싱/복구, 안전한 파일 입출력, 컨텍스트 블록 인코딩.
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

CONTEXT_BEGIN = "<<<HACO_CONTEXT_JSON>>>"
CONTEXT_END = "<<<END_HACO_CONTEXT_JSON>>>"


def now_run_id() -> str:
    """결정적이지 않은 현재 시각 기반 run id."""
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def estimate_tokens(text: str) -> int:
    """char/4 기반 단순 토큰 추정 (계약서 §16)."""
    return max(0, len(text) // 4)


def read_text(path: str | Path, default: str = "") -> str:
    p = Path(path)
    if not p.exists():
        return default
    return p.read_text(encoding="utf-8", errors="replace")


def write_text(path: str | Path, content: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def write_json(path: str | Path, data: Any) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


def read_json(path: str | Path, default: Any = None) -> Any:
    text = read_text(path)
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def encode_context_block(context: dict) -> str:
    """워커 프롬프트에 끼워 넣을 머신리더블 컨텍스트 블록."""
    body = json.dumps(context, ensure_ascii=False)
    return f"{CONTEXT_BEGIN}\n{body}\n{CONTEXT_END}"


def decode_context_block(prompt: str) -> dict:
    """프롬프트에서 컨텍스트 블록을 추출한다. 없으면 빈 dict."""
    start = prompt.find(CONTEXT_BEGIN)
    end = prompt.find(CONTEXT_END)
    if start == -1 or end == -1 or end < start:
        return {}
    body = prompt[start + len(CONTEXT_BEGIN):end].strip()
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {}


def repair_and_parse_json(text: str) -> Any:
    """LLM JSON 응답을 파싱한다. 실패 시 가벼운 복구를 시도한다.

    복구 실패 시 json.JSONDecodeError를 올린다.
    """
    text = text.strip()
    # markdown code fence 제거
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```$", "", text)
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 첫 { 와 마지막 } 사이만 추출
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        candidate = text[first:last + 1]
        # 흔한 trailing comma 제거
        candidate = re.sub(r",(\s*[}\]])", r"\1", candidate)
        return json.loads(candidate)
    return json.loads(text)  # 최종 실패 → 예외 전파


def clamp_str(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"
