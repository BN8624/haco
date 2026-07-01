# 결정론적 context pack 생성기: 파일 전체가 아니라 심볼/섹션/키워드 범위 excerpt를 뽑는다(§9, §27).
from __future__ import annotations

from pathlib import Path

from haco.config import Config
from haco.schemas import TaskPacket
from haco.utils import estimate_tokens

# §17.1 recommended thresholds. LLM이 아니라 결정론 코드가 범위를 좁히는 pollution 방지 게이트.
MAX_FILES = 5              # MAX_FILES_MEDIUM
MAX_RANGE_LINES = 200      # MAX_RANGE_LINES_HIGH
KEYWORD_WINDOW = 40        # 키워드 앞뒤로 읽을 라인 수
MAX_SYMBOLS_PER_FILE = 3   # 파일당 excerpt로 뽑을 심볼 상한
DEFAULT_MAX_TOKENS = 8000  # MAX_CONTEXT_PACK_TOKENS

_CODE_SUFFIXES = (".py", ".js", ".jsx", ".ts", ".tsx", ".rs", ".go")
_DOC_SUFFIXES = (".md", ".rst")


def _read_lines(path: Path) -> list[str] | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None


def _excerpt(lines: list[str], start: int, end: int) -> tuple[str, int, int, bool]:
    """1-indexed [start, end]를 MAX_RANGE_LINES로 제한해 excerpt 문자열을 만든다."""
    start = max(1, start)
    end = min(len(lines), max(start, end))
    truncated = (end - start + 1) > MAX_RANGE_LINES
    if truncated:
        end = start + MAX_RANGE_LINES - 1
    body = "\n".join(lines[start - 1:end])
    return body, start, end, truncated


def _match_keyword(text: str, keywords: list[str]) -> bool:
    low = text.lower()
    return any(k.lower() in low for k in keywords if k)


def _markdown_section(lines: list[str], keywords: list[str]) -> tuple[int, int] | None:
    """키워드와 맞는 heading 섹션의 [start, end]를 반환. 없으면 첫 heading 섹션."""
    heads = [i for i, ln in enumerate(lines) if ln.lstrip().startswith("#")]
    if not heads:
        return None
    chosen = None
    if keywords:
        for i in heads:
            if _match_keyword(lines[i], keywords):
                chosen = i
                break
    if chosen is None:
        chosen = heads[0]
    nxt = next((h for h in heads if h > chosen), len(lines))
    return chosen + 1, nxt  # 1-indexed, 다음 heading 직전까지


def _keyword_window(lines: list[str], keywords: list[str]) -> tuple[int, int] | None:
    if not keywords:
        return None
    for i, ln in enumerate(lines):
        if _match_keyword(ln, keywords):
            return max(1, i + 1 - KEYWORD_WINDOW), min(len(lines), i + 1 + KEYWORD_WINDOW)
    return None


def _symbol_entries(rel: str, lines: list[str], symbols: list[dict],
                    keywords: list[str]) -> list[dict]:
    """repo_map 심볼(line 범위 보유) 기준 excerpt 항목들을 만든다."""
    ranged = [s for s in symbols
              if isinstance(s, dict) and s.get("line_start")]
    if not ranged:
        return []
    # 키워드와 맞는 심볼을 먼저, 그 다음 등장 순서. 결정론적.
    matched = [s for s in ranged if _match_keyword(
        f"{s.get('name', '')} {s.get('signature', '')}", keywords)]
    ordered = matched + [s for s in ranged if s not in matched]
    entries: list[dict] = []
    for s in ordered[:MAX_SYMBOLS_PER_FILE]:
        ls = int(s["line_start"])
        le = int(s.get("line_end") or ls)
        body, ls, le, trunc = _excerpt(lines, ls, le)
        entries.append({
            "file": rel, "kind": "symbol", "symbol": s.get("name", ""),
            "signature": s.get("signature", ""),
            "line_start": ls, "line_end": le, "excerpt": body,
            "reason": f"{s.get('kind', 'symbol')} `{s.get('name', '')}` "
                      f"matched the task" if s in matched
                      else f"{s.get('kind', 'symbol')} `{s.get('name', '')}` in target file",
            "excerpt_truncated": trunc,
        })
    return entries


def _file_entries(project_path: Path, rel: str, repo_index: dict,
                  keywords: list[str]) -> tuple[list[dict], str]:
    """한 파일에 대한 excerpt 항목들과 skip 사유(있으면)를 반환한다."""
    path = project_path / rel
    if not path.exists() or not path.is_file():
        return [], f"{rel}: not found on disk"
    lines = _read_lines(path)
    if lines is None:
        return [], f"{rel}: unreadable"

    suffix = path.suffix.lower()
    if suffix in _CODE_SUFFIXES and repo_index.get(rel):
        entries = _symbol_entries(rel, lines, repo_index[rel], keywords)
        if entries:
            return entries, ""
    if suffix in _DOC_SUFFIXES:
        rng = _markdown_section(lines, keywords)
        if rng:
            body, ls, le, trunc = _excerpt(lines, *rng)
            return [{
                "file": rel, "kind": "markdown_section", "symbol": lines[ls - 1].strip(),
                "line_start": ls, "line_end": le, "excerpt": body,
                "reason": "markdown heading section relevant to the task",
                "excerpt_truncated": trunc,
            }], ""
    # 폴백: 키워드 윈도우
    rng = _keyword_window(lines, keywords)
    if rng:
        body, ls, le, trunc = _excerpt(lines, *rng)
        return [{
            "file": rel, "kind": "keyword_window", "symbol": "",
            "line_start": ls, "line_end": le, "excerpt": body,
            "reason": "window around the first keyword match",
            "excerpt_truncated": trunc,
        }], ""
    return [], f"{rel}: no symbol/section/keyword range could be narrowed"


def _render_md(entries: list[dict], omitted: list[str], notes: list[str],
               token_est: int, max_tokens: int) -> str:
    out = ["# HACO Context Pack", "",
           "Focused excerpts instead of whole files. "
           "Read these ranges first; the reason and omissions are noted per entry.",
           ""]
    if not entries:
        out += ["> No useful focused context could be built.",
                "> " + (notes[0] if notes else "No narrowable ranges found."),
                "> Proceed with bounded exploration from files_to_read.", ""]
    for e in entries:
        loc = f"{e['file']}:{e['line_start']}-{e['line_end']}"
        head = f"## {loc}"
        if e.get("symbol"):
            head += f"  ({e['symbol']})"
        out.append(head)
        out.append("")
        out.append(f"- Why: {e['reason']}")
        if e.get("excerpt_truncated"):
            out.append(f"- Omitted: excerpt truncated to {MAX_RANGE_LINES} lines")
        out.append("")
        out.append("```")
        out.append(e["excerpt"])
        out.append("```")
        out.append("")
    if omitted:
        out.append("## Omitted")
        out.append("")
        for o in omitted:
            out.append(f"- {o}")
        out.append("")
    out.append(f"<!-- context_pack tokens≈{token_est} / budget {max_tokens} -->")
    return "\n".join(out) + "\n"


def build_context_pack(*, project_path: Path, snapshot: dict, packet: TaskPacket,
                       config: Config) -> tuple[str, dict]:
    """files_to_read + repo_map 범위로 결정론적 context pack(md, json)을 만든다.

    저신뢰(skip)면 fail closed: 짧은 pack만 남긴다. budget 초과분은 omitted로 기록한다.
    """
    project_path = Path(project_path)
    max_tokens = config.get("budgets", "max_context_pack_tokens",
                            default=DEFAULT_MAX_TOKENS)
    keywords = list(packet.search_keywords or [])

    repo_index = {item["file"]: item.get("symbols", [])
                  for item in snapshot.get("repo_map", []) or []
                  if isinstance(item, dict) and item.get("file")}

    # 대상 파일: files_to_read 우선, 그 다음 files_to_edit(중복 제거, 순서 보존).
    targets: list[str] = []
    for rel in list(packet.files_to_read or []) + list(packet.files_to_edit or []):
        if rel and rel not in targets:
            targets.append(rel)

    status = "ready"
    notes: list[str] = []
    if packet.haco_status == "skip_to_main_agent":
        status = "skipped"
        notes.append("haco_status=skip_to_main_agent; context pack kept minimal (fail closed).")
        targets = []
    elif not targets:
        status = "empty"
        notes.append("No files_to_read; nothing to offload.")

    entries: list[dict] = []
    omitted: list[str] = []
    token_est = 0
    for rel in targets[:MAX_FILES]:
        file_entries, skip_note = _file_entries(project_path, rel, repo_index, keywords)
        if skip_note:
            omitted.append(skip_note)
            continue
        for e in file_entries:
            cost = estimate_tokens(e["excerpt"])
            if token_est + cost > max_tokens and entries:
                omitted.append(f"{e['file']}:{e['line_start']}-{e['line_end']} "
                               f"(context pack token budget {max_tokens} reached)")
                continue
            entries.append(e)
            token_est += cost
    for rel in targets[MAX_FILES:]:
        omitted.append(f"{rel}: beyond MAX_FILES={MAX_FILES}")

    cp_json = {
        "status": status,
        "files": [{k: v for k, v in e.items() if k != "excerpt"} for e in entries],
        "budget": {"token_estimate": token_est, "max_tokens": max_tokens},
        "omitted": omitted,
        "notes": notes,
    }
    return _render_md(entries, omitted, notes, token_est, max_tokens), cp_json
