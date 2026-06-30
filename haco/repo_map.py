# 프로젝트 구조 뼈대를 작게 요약하는 repository map 생성기 (Python AST + best-effort regex).
from __future__ import annotations

import ast
import re
from pathlib import Path

DOCSTRING_PREVIEW_CHARS = 120


def _docstring_preview(node: ast.AST) -> str:
    try:
        doc = ast.get_docstring(node)  # type: ignore[arg-type]
    except TypeError:
        doc = None
    if not doc:
        return ""
    first = doc.strip().splitlines()[0] if doc.strip() else ""
    return first[:DOCSTRING_PREVIEW_CHARS]


def _format_args(node: ast.AST) -> str:
    args = getattr(node, "args", None)
    if args is None:
        return ""
    parts: list[str] = []
    for a in args.args:
        ann = ""
        if a.annotation is not None:
            try:
                ann = ": " + ast.unparse(a.annotation)
            except Exception:
                ann = ""
        parts.append(a.arg + ann)
    if args.vararg:
        parts.append("*" + args.vararg.arg)
    if args.kwarg:
        parts.append("**" + args.kwarg.arg)
    return ", ".join(parts)


def extract_python_symbols(source: str) -> list[dict]:
    """Python 소스에서 class/function/import 심볼을 추출한다. 파싱 실패 시 예외."""
    tree = ast.parse(source)
    symbols: list[dict] = []
    imports: list[str] = []

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                imports.extend(n.name for n in node.names)
            else:
                mod = node.module or ""
                imports.append(mod)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            ret = ""
            if node.returns is not None:
                try:
                    ret = " -> " + ast.unparse(node.returns)
                except Exception:
                    ret = ""
            symbols.append({
                "kind": "function",
                "name": node.name,
                "signature": f"{node.name}({_format_args(node)}){ret}",
                "docstring_preview": _docstring_preview(node),
            })
        elif isinstance(node, ast.ClassDef):
            methods = [n.name for n in node.body
                       if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            symbols.append({
                "kind": "class",
                "name": node.name,
                "signature": f"class {node.name}",
                "methods": methods[:12],
                "docstring_preview": _docstring_preview(node),
            })

    result = symbols
    if imports:
        result = [{"kind": "imports", "names": sorted(set(imports))[:30]}] + symbols
    return result


_REGEX_HINTS = {
    ".js": [r"export\s+(?:default\s+)?(?:async\s+)?function\s+(\w+)",
            r"export\s+class\s+(\w+)", r"function\s+(\w+)", r"class\s+(\w+)"],
    ".jsx": [r"export\s+(?:default\s+)?function\s+(\w+)", r"function\s+(\w+)",
             r"class\s+(\w+)"],
    ".ts": [r"export\s+(?:async\s+)?function\s+(\w+)", r"export\s+class\s+(\w+)",
            r"export\s+interface\s+(\w+)", r"function\s+(\w+)", r"class\s+(\w+)"],
    ".tsx": [r"export\s+(?:async\s+)?function\s+(\w+)", r"export\s+class\s+(\w+)",
             r"function\s+(\w+)"],
    ".rs": [r"pub\s+fn\s+(\w+)", r"\bfn\s+(\w+)", r"pub\s+struct\s+(\w+)",
            r"\bstruct\s+(\w+)", r"\benum\s+(\w+)", r"\bmod\s+(\w+)"],
    ".go": [r"func\s+(\w+)", r"type\s+(\w+)\s+struct", r"type\s+(\w+)"],
}


def extract_regex_symbols(source: str, suffix: str) -> list[dict]:
    """Python 외 언어에 대한 best-effort 정규식 symbol hint."""
    patterns = _REGEX_HINTS.get(suffix, [])
    names: list[str] = []
    for pat in patterns:
        for m in re.finditer(pat, source):
            names.append(m.group(1))
    seen: list[dict] = []
    for n in dict.fromkeys(names):  # 순서 보존 dedup
        seen.append({"kind": "symbol_hint", "name": n})
    return seen[:40]


def build_repo_map(project_path: Path, file_paths: list[str],
                   max_files: int = 120) -> tuple[list[dict], str, list[str]]:
    """파일 경로 목록으로 repo_map을 만든다.

    반환: (repo_map, status, notes). status: ok | partial | skipped
    """
    repo_map: list[dict] = []
    notes: list[str] = []
    parse_failures = 0
    processed = 0

    for rel in file_paths:
        if processed >= max_files:
            notes.append(f"repo_map truncated to {max_files} files.")
            break
        path = Path(project_path) / rel
        suffix = path.suffix.lower()
        if suffix not in (".py", ".js", ".jsx", ".ts", ".tsx", ".rs", ".go"):
            continue
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        processed += 1
        try:
            if suffix == ".py":
                symbols = extract_python_symbols(source)
            else:
                symbols = extract_regex_symbols(source, suffix)
        except SyntaxError:
            parse_failures += 1
            repo_map.append({"file": rel, "symbols": [],
                             "note": "parse_failed_fallback"})
            continue
        except Exception:
            parse_failures += 1
            continue
        if symbols:
            repo_map.append({"file": rel, "symbols": symbols})

    if not repo_map:
        status = "skipped"
    elif parse_failures > 0:
        status = "partial"
        notes.append(f"{parse_failures} file(s) failed to parse; used fallback.")
    else:
        status = "ok"
    return repo_map, status, notes
