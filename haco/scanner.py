# 대상 프로젝트를 가볍게 스캔해 project_snapshot 을 만든다 (worker 호출 전 단계).
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from haco.config import Config
from haco.repo_map import build_repo_map

IMPORTANT_NAMES = [
    "README.md", "README.rst", "AGENTS.md", "CLAUDE.md", "pyproject.toml",
    "setup.py", "setup.cfg", "requirements.txt", "package.json", "tsconfig.json",
    "Cargo.toml", "go.mod", "Makefile", "Dockerfile", "pytest.ini", "tox.ini",
]


def _iter_files(root: Path, ignore_dirs: set[str], max_files: int) -> list[str]:
    out: list[str] = []
    for dirpath, dirnames, filenames in __import__("os").walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs and
                       not d.startswith(".egg-info")]
        for f in filenames:
            rel = str(Path(dirpath, f).relative_to(root)).replace("\\", "/")
            out.append(rel)
            if len(out) >= max_files:
                return out
    return out


def _tree_preview(root: Path, ignore_dirs: set[str], depth: int) -> list[str]:
    lines: list[str] = []
    for dirpath, dirnames, filenames in __import__("os").walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
        rel = Path(dirpath).relative_to(root)
        level = 0 if str(rel) == "." else len(rel.parts)
        if level > depth:
            dirnames[:] = []
            continue
        indent = "  " * level
        name = root.name if str(rel) == "." else rel.parts[-1]
        lines.append(f"{indent}{name}/")
        for f in sorted(filenames)[:20]:
            lines.append(f"{indent}  {f}")
        if len(lines) > 200:
            break
    return lines[:200]


def _detect_language(file_paths: list[str], important: list[str]) -> str:
    counts: dict[str, int] = {}
    for p in file_paths:
        ext = Path(p).suffix.lower()
        counts[ext] = counts.get(ext, 0) + 1
    if "pyproject.toml" in important or "setup.py" in important or \
            "requirements.txt" in important or counts.get(".py", 0) > 0:
        if counts.get(".py", 0) >= max(counts.get(".ts", 0), counts.get(".js", 0),
                                       counts.get(".rs", 0), counts.get(".go", 0)):
            return "python"
    if counts.get(".ts", 0) > 0 or "tsconfig.json" in important:
        return "typescript"
    if counts.get(".js", 0) > 0 or "package.json" in important:
        return "javascript"
    if counts.get(".rs", 0) > 0 or "Cargo.toml" in important:
        return "rust"
    if counts.get(".go", 0) > 0 or "go.mod" in important:
        return "go"
    if counts.get(".py", 0) > 0:
        return "python"
    return "unknown"


def _detect_project_type(language: str, important: list[str]) -> str:
    if "pyproject.toml" in important or "setup.py" in important:
        return "python_package"
    if "package.json" in important:
        return "node_package"
    if "Cargo.toml" in important:
        return "rust_crate"
    if "go.mod" in important:
        return "go_module"
    if language != "unknown":
        return "generic"
    return "unknown"


def _detect_test_frameworks(project_path: Path, important: list[str],
                            file_paths: list[str]) -> list[str]:
    fw: list[str] = []
    pyproject = project_path / "pyproject.toml"
    if "pytest.ini" in important or "tox.ini" in important:
        fw.append("pytest")
    elif pyproject.exists() and "pytest" in pyproject.read_text(
            encoding="utf-8", errors="replace"):
        fw.append("pytest")
    elif any(re.search(r"(^|/)tests?/.*test_.*\.py$", p) or
             re.search(r"test_.*\.py$", p) for p in file_paths):
        fw.append("pytest")
    pkg = project_path / "package.json"
    if pkg.exists():
        txt = pkg.read_text(encoding="utf-8", errors="replace")
        if "vitest" in txt:
            fw.append("vitest")
        elif "jest" in txt:
            fw.append("jest")
        elif '"test"' in txt:
            fw.append("npm test")
    if any(p == "vitest.config.ts" or p.startswith("vitest.config") for p in file_paths):
        if "vitest" not in fw:
            fw.append("vitest")
    if "Cargo.toml" in important:
        fw.append("cargo test")
    if "go.mod" in important:
        fw.append("go test")
    return list(dict.fromkeys(fw))


def _git_ignored_paths(project_path: Path, file_paths: list[str]) -> set[str]:
    """git check-ignore로 무시되는 rel 경로 집합을 반환. git이 없거나 repo가 아니면 빈 집합.

    한 번의 `git check-ignore --stdin` 호출로 전체 경로를 일괄 판정한다(파일당 호출 금지).
    종료코드 0=일부 무시, 1=무시 없음, 그 외(128 등)=repo 아님/오류 → 필터 미적용.
    """
    if not file_paths:
        return set()
    # -z(NUL 구분) + bytes로 호출한다. text 모드는 Windows에서 stdin의 \n을 \r\n으로 바꿔
    # git이 경로에 \r를 포함시키고 core.quotePath로 따옴표까지 씌워 매칭이 깨진다. -z는 양방향
    # NUL 구분이라 그 변환/따옴표 문제가 없다.
    try:
        proc = subprocess.run(
            ["git", "-C", str(project_path), "check-ignore", "-z", "--stdin"],
            input="\0".join(file_paths).encode("utf-8"),
            capture_output=True, timeout=10,
        )
    except Exception:
        return set()
    if proc.returncode not in (0, 1):
        return set()
    out = proc.stdout.decode("utf-8", "replace")
    return {p.replace("\\", "/") for p in out.split("\0") if p}


def _git_status(project_path: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(project_path), "status", "--porcelain"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=10,
        )
        if out.returncode == 0:
            return out.stdout.strip()[:2000]
    except Exception:
        pass
    return ""


def _recent_files(project_path: Path, file_paths: list[str], n: int = 15) -> list[str]:
    with_mtime = []
    for rel in file_paths:
        p = project_path / rel
        try:
            with_mtime.append((p.stat().st_mtime, rel))
        except OSError:
            continue
    with_mtime.sort(reverse=True)
    return [rel for _, rel in with_mtime[:n]]


def _extract_keywords(task: str) -> list[str]:
    # 한글/영문/숫자/underscore 혼합 토큰을 추출한다. phase2f, ticks10000, 10k 같은
    # 혼합 패턴과 한국어 작업 지시(검증, 문서 등)를 살리되, 영어 식별자 동작은 보존한다.
    tokens = re.findall(r"[가-힣A-Za-z0-9_]+", task)
    stop = {"the", "and", "for", "add", "fix", "use", "this", "that", "with",
            "into", "from", "should", "must", "make", "run", "test", "tests"}
    out: list[str] = []
    for t in tokens:
        s = t.strip("_")
        if not s or not any(c.isalnum() for c in s) or len(s) > 40:
            continue  # 빈 토큰/언더스코어 잡음/과도하게 긴 토큰 제외
        low = s.lower()
        if low in stop:
            continue
        has_digit = any(c.isdigit() for c in s)
        has_hangul = any("가" <= c <= "힣" for c in s)
        # 한글·혼합(숫자 포함) 토큰은 짧아도 의미가 있어 유지. 순수 영문은 기존대로 3자 이상.
        if not (has_hangul or has_digit) and len(s) < 3:
            continue
        out.append(s)
    # Intent Expansion: 코드 식별자(함수/상수/파일 stem)를 일반 산문어보다 앞에 둔다. locator가
    # 상위 소수만 쓰거나(예: [:8]) 목록을 자를 때 식별자가 잘려나가지 않게 한다. 안정 정렬로 원래
    # 순서는 그룹 안에서 보존한다.
    deduped = list(dict.fromkeys(out))
    idents = [t for t in deduped if _is_identifier_like(t)]
    rest = [t for t in deduped if not _is_identifier_like(t)]
    return (idents + rest)[:20]


def _is_identifier_like(token: str) -> bool:
    """코드 식별자스러운 토큰인지. snake_case/camelCase/숫자혼합(phase5a, ticks10000)/ALLCAPS 상수."""
    if "_" in token:
        return True
    has_alpha = any(c.isalpha() for c in token)
    has_digit = any(c.isdigit() for c in token)
    if has_alpha and has_digit:
        return True  # phase5a, ticks10000, verify_phase2f 류
    # 첫 글자 외 대문자 → camelCase 또는 ALLCAPS 상수(GODSEED, calculateGrowth)
    if any(c.isupper() for c in token[1:]):
        return True
    return False


def _symbol_index(repo_map: list[dict] | None) -> dict[str, set[str]]:
    """파일(rel, lower) → 그 파일 심볼 이름 집합(lower). content-aware 랭킹용."""
    index: dict[str, set[str]] = {}
    for it in repo_map or []:
        if not (isinstance(it, dict) and it.get("file")):
            continue
        names: set[str] = set()
        for s in it.get("symbols", []) or []:
            if isinstance(s, dict):
                if s.get("name"):
                    names.add(s["name"].lower())
                names.update(m.lower() for m in s.get("methods", []) or [])
        index[it["file"].lower()] = names
    return index


def _keyword_matches(keywords: list[str], file_paths: list[str],
                     repo_map: list[dict] | None = None) -> list[str]:
    # 관련도순 정렬. 점수 = Σ (키워드 길이 / 해당 키워드의 document-frequency).
    # - 길이: 구체적인(긴) 키워드일수록 강하게.
    # - df로 나눔: 여러 파일에 흔히 등장하는 키워드("docs","validation")는 약하게,
    #   소수 파일에만 맞는 희귀 키워드("verify_phase2f")는 강하게.
    # 등장 순서가 아니라 이 점수로 정렬해야 실제 타깃이 흔한 키워드 매칭에 묻히지 않는다.
    # content-aware: 파일명이 안 맞아도 그 파일의 repo_map 심볼 이름이 키워드와 맞으면 boost한다
    #   (예: phase0_engine.py는 이름에 "starvation"이 없지만 compute_starvation_pressure를 보유).
    # 편집 가능성이 낮은 archive/deprecated/vendor 경로는 점수를 낮춰 live 파일에 밀리게 한다.
    downrank = ("/archive/", "archive/", "/deprecated/", "deprecated/",
                "/vendor/", "vendor/", "/third_party/", "third_party/")
    lowered = [(p, p.lower()) for p in file_paths]
    kws = [k.lower() for k in keywords if k]
    df = {k: sum(1 for _, low in lowered if k in low) for k in kws}
    sym_index = _symbol_index(repo_map)
    scored: list[tuple[float, str]] = []
    for orig, low in lowered:
        base = low.rsplit("/", 1)[-1]
        stem = base.rsplit(".", 1)[0]
        names = sym_index.get(low, set())
        score = 0.0
        for k in kws:
            # content 매칭: 키워드가 그 파일 심볼 이름이면(정확) 강한 boost, 부분매칭은 약하게.
            # df로 나누지 않는다(content df는 path df와 다르며, 심볼명 매칭은 고신호).
            if k in names:
                score += len(k) * 2.0
            elif names and any(k in nm or nm in k for nm in names):
                score += len(k) * 0.75
            if not df.get(k) or k not in low:
                continue
            # 파일명 매칭은 경로 어딘가 매칭보다 강하게. task가 명시한 파일 stem 정확매칭은 최상.
            # (verify_phase5a가 keyword면 verify_phase5a.py가 verify_phase3a.py보다 확실히 앞선다.)
            weight = len(k) / df[k]
            if k == stem:
                weight *= 4.0
            elif k in base:
                weight *= 2.0
            score += weight
        if score:
            if low.startswith(("archive/", "deprecated/")) or any(s in low for s in downrank):
                score *= 0.2
            scored.append((score, orig))
    scored.sort(key=lambda x: (-x[0], x[1]))  # 점수 desc, path asc (결정적)
    return [orig for _, orig in scored[:30]]


def scan_project(project_path: Path, task: str, config: Config) -> dict:
    """대상 프로젝트를 스캔해 project_snapshot dict를 반환한다."""
    project_path = Path(project_path)
    sc = config.get("scanner", default={})
    ignore_dirs = set(sc.get("ignore_dirs", []))
    depth = sc.get("include_tree_depth", 3)
    max_files = config.get("limits", "max_files_in_snapshot", default=300)

    file_paths = _iter_files(project_path, ignore_dirs, max_files)
    # gitignore 산출물(예: root scratch *_summary.json)은 편집 대상이 아니므로 제외해
    # keyword_matches/files_to_read 노이즈를 줄인다. git 없으면 무필터.
    if sc.get("respect_gitignore", True):
        ignored = _git_ignored_paths(project_path, file_paths)
        if ignored:
            file_paths = [p for p in file_paths if p not in ignored]
    important = [p for p in file_paths if Path(p).name in IMPORTANT_NAMES]
    important_names = [Path(p).name for p in important]

    language = _detect_language(file_paths, important_names)
    project_type = _detect_project_type(language, important_names)
    test_frameworks = _detect_test_frameworks(project_path, important_names, file_paths)

    # repo_map을 먼저 만들어 content-aware 키워드 랭킹(심볼 이름 매칭)에 넘긴다.
    repo_map: list[dict] = []
    repo_map_status = "skipped"
    repo_map_notes: list[str] = []
    if sc.get("include_repo_map", True):
        repo_map, repo_map_status, repo_map_notes = build_repo_map(
            project_path, file_paths)

    keywords = _extract_keywords(task)
    keyword_matches = _keyword_matches(keywords, file_paths, repo_map)

    readme_preview = ""
    if sc.get("include_readme_preview", True):
        for cand in ("README.md", "README.rst"):
            rp = project_path / cand
            if rp.exists():
                readme_preview = rp.read_text(
                    encoding="utf-8", errors="replace")[:1000]
                break

    snapshot = {
        "project_path": str(project_path),
        "primary_language": language,
        "project_type": project_type,
        "test_frameworks": test_frameworks,
        "package_files": [p for p in important
                          if Path(p).name in (
                              "pyproject.toml", "package.json", "Cargo.toml",
                              "go.mod", "setup.py", "requirements.txt")],
        "tree_preview": _tree_preview(project_path, ignore_dirs, depth),
        "file_paths_sample": file_paths[:200],
        "git_status": _git_status(project_path) if sc.get("include_git_status", True) else "",
        "recent_files": _recent_files(project_path, file_paths)
        if sc.get("include_recent_files", True) else [],
        "important_files": important,
        "readme_preview": readme_preview,
        "keyword_file_matches": keyword_matches,
        "search_hints": keywords,
        "repo_map": repo_map,
        "repo_map_status": repo_map_status,
        "repo_map_notes": repo_map_notes,
        "truncation_applied": False,
        "truncation_notes": [],
        "notes": [],
    }
    return snapshot
