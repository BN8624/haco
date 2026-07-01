# file_locator 결과를 결정론 content-aware 랭킹으로 최종 보정한다 (LLM은 제안자, 랭커가 순서 확정).
from __future__ import annotations

from haco.config import Config

# confidence.MAX_FILES_MEDIUM 과 동일. 초과분은 잘라 context pack pollution 을 막는다.
MAX_FILES_MEDIUM = 5


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


def _score(rel: str, hints: list[str], sym_index: dict[str, set[str]]) -> float:
    """scanner._keyword_matches 와 같은 결정론 content-aware 점수. 심볼명 매칭 + 파일명 매칭."""
    low = rel.lower()
    base = low.rsplit("/", 1)[-1]
    stem = base.rsplit(".", 1)[0]
    names = sym_index.get(low, set())
    score = 0.0
    for k in hints:
        if not k:
            continue
        k = k.lower()
        if k in names:
            score += len(k) * 2.0          # content 정확매칭(심볼명): 파일명이 안 맞아도 상위화
        elif names and any(k in nm or nm in k for nm in names):
            score += len(k) * 0.75         # content 부분매칭
        if k == stem:
            score += len(k) * 4.0          # 파일명 stem 정확매칭이 최상
        elif k in base:
            score += len(k) * 2.0          # 파일명 부분매칭
        elif k in low:
            score += len(k) * 1.0          # 경로 어딘가 매칭
    return score


def post_locator_rerank(locator: dict, snapshot: dict,
                        config: Config | None = None) -> dict:
    """locator.files_to_read/edit 와 snapshot.keyword_file_matches 를 합쳐 재정렬한다.

    LLM locator 는 제안자이고, 이 결정론 랭커가 최종 파일 순서를 확정한다. worker 가 medium/high
    confidence 로 엉뚱한 파일을 줘도 content-aware top 이 다르면 그 파일을 상위로 올린다.

    반환: locator 사본. files_to_read/files_to_edit 재정렬 + locator_adjusted/
    locator_adjust_reason 기록. 결정론 근거(score>0)가 없으면 locator 원본을 신뢰(fail-closed).
    """
    files_to_read = [f for f in (locator.get("files_to_read") or []) if f]
    files_to_edit = [f for f in (locator.get("files_to_edit") or []) if f]
    kw_matches = [f for f in (snapshot.get("keyword_file_matches") or []) if f]
    hints = (list(snapshot.get("search_hints") or [])
             or list(locator.get("search_keywords") or []))
    sym_index = _symbol_index(snapshot.get("repo_map", []))

    result = dict(locator)
    result["locator_adjusted"] = False
    result["locator_adjust_reason"] = ""

    # 후보 풀: locator 제안(read+edit) + 결정론 keyword 매칭. 합집합, 최초 등장 순서 보존.
    pool: list[str] = []
    for f in files_to_read + files_to_edit + kw_matches:
        if f not in pool:
            pool.append(f)
    if not pool:
        return result

    order = {f: i for i, f in enumerate(pool)}
    scored = sorted(pool, key=lambda f: (-_score(f, hints, sym_index), order[f]))
    top_score = _score(scored[0], hints, sym_index)

    # 근거가 없으면(모든 점수 0) 재정렬/확장하지 않고 locator 원본 유지. 억지 보정 금지(fail-closed).
    if top_score <= 0:
        return result

    reranked_read = scored[:MAX_FILES_MEDIUM]
    # files_to_edit 는 locator 가 지목한 편집 대상만 유지하되 결정론 순서로 재정렬한다.
    # 편집 대상을 새로 발명하지 않는다(잘못된 파일을 실수로 편집시키는 위험 회피).
    edit_set = set(files_to_edit)
    reranked_edit = [f for f in scored if f in edit_set]

    old_top = files_to_read[0] if files_to_read else ""
    new_top = reranked_read[0]
    if new_top != old_top:
        result["locator_adjusted"] = True
        if old_top:
            result["locator_adjust_reason"] = (
                f"deterministic content-aware rerank promoted {new_top} over {old_top}")
        else:
            result["locator_adjust_reason"] = (
                f"locator returned no files_to_read; deterministic ranking supplied {new_top}")

    result["files_to_read"] = reranked_read
    result["files_to_edit"] = reranked_edit
    return result
