# 결정론 evidence 기반 confidence 판정기(§17.1): Hard Gate → Evidence Score → Tier.
from __future__ import annotations

from haco.config import Config

# §17.1 recommended initial thresholds. LLM self-report이 아니라 결정론 신호로 tier를 정한다.
HIGH_THRESHOLD = 70
MEDIUM_THRESHOLD = 45
MAX_FILES_HIGH = 3
MAX_FILES_MEDIUM = 5
MIN_DETERMINISTIC_SIGNALS_HIGH = 2


def _known_paths(snapshot: dict) -> set[str]:
    known = set(snapshot.get("file_paths_sample", []) or [])
    for item in snapshot.get("repo_map", []) or []:
        if isinstance(item, dict) and item.get("file"):
            known.add(item["file"])
    return known


def evaluate_confidence(*, snapshot: dict, locator: dict, context_pack_json: dict,
                        task_type: str, config: Config) -> dict:
    """결정론 신호로 confidence tier와 fail-closed 여부를 판정한다.

    반환 dict: fail_closed_triggered, fail_closed_reason, confidence_tier,
    evidence_score, deterministic_signal_count, hard_gates_triggered.
    LLM이 보고한 locator confidence는 참고만 하고 최종 판정 근거로 쓰지 않는다.
    """
    files_to_read = list(locator.get("files_to_read", []) or [])
    n_files = len(files_to_read)
    known = _known_paths(snapshot)
    # 파일별 실제 symbols. "파일이 repo_map에 있음"과 "symbols가 있음"을 구분한다.
    repo_syms = {item["file"]: item.get("symbols", []) or []
                 for item in snapshot.get("repo_map", []) or []
                 if isinstance(item, dict) and item.get("file")}
    keywords = [k.lower() for k in (locator.get("search_keywords") or []) if k]
    cp_files = context_pack_json.get("files", []) or []
    cp_kinds = [f.get("kind") for f in cp_files]
    n_ranges = len(cp_files)
    budget = context_pack_json.get("budget", {}) or {}
    max_tokens = config.get("budgets", "max_context_pack_tokens", default=8000)

    def _keyword_hits_symbol() -> bool:
        for f in files_to_read:
            for s in repo_syms.get(f, []):
                blob = f"{s.get('name', '')} {s.get('signature', '')}".lower()
                if any(k in blob for k in keywords):
                    return True
        return False

    # ---- 결정론 신호 카운트 ----
    signals: list[str] = []
    if files_to_read and any(f in known for f in files_to_read):
        signals.append("path_evidence")               # 실재하는 파일 경로
    # symbol evidence: 대상 파일에 실제 symbols가 있고, context_pack이 symbol excerpt를
    # 만들었거나 task keyword가 symbol name/signature와 매칭될 때만(단순 "파일 존재" 불충분).
    has_real_symbols = any(repo_syms.get(f) for f in files_to_read)
    if has_real_symbols and ("symbol" in cp_kinds or _keyword_hits_symbol()):
        signals.append("symbol_evidence")
    if n_ranges > 0:
        signals.append("range_evidence")              # focused 범위 확보
    # keyword evidence: files_to_read 안에서 실제 keyword window가 만들어졌을 때만
    # (snapshot 어딘가의 무관한 keyword match로 점수가 부풀지 않게).
    if "keyword_window" in cp_kinds:
        signals.append("keyword_evidence")
    det_count = len(signals)

    # ---- Hard Gates (§17.1) ----
    gates: list[str] = []
    if task_type in ("", "unknown"):
        gates.append("task_intent_unclassified")
    if n_files > MAX_FILES_MEDIUM:
        gates.append("too_many_files")
    if files_to_read and n_ranges == 0:
        gates.append("no_symbol_section_or_range")
    if det_count == 0:
        gates.append("no_deterministic_evidence")
    if budget.get("token_estimate", 0) > max_tokens:
        gates.append("context_pack_over_budget")

    # ---- Evidence Score (0-100, 결정론) ----
    score = 0
    if "path_evidence" in signals:
        score += 30
    if "range_evidence" in signals:
        score += 30
    if "symbol_evidence" in signals:
        score += 20
    if 0 < n_files <= MAX_FILES_HIGH:
        score += 20
    score = min(100, score)

    # ---- Tier ----
    if gates:
        tier, fail_closed = "low", True
        reason = gates[0]
    elif (score >= HIGH_THRESHOLD and det_count >= MIN_DETERMINISTIC_SIGNALS_HIGH
          and n_files <= MAX_FILES_HIGH):
        tier, fail_closed, reason = "high", False, ""
    elif score >= MEDIUM_THRESHOLD:
        tier, fail_closed, reason = "medium", False, ""
    else:
        # 저신뢰는 fail closed(§17.1: haco_status=skip_to_main_agent).
        tier, fail_closed, reason = "low", True, "low_confidence_score"

    return {
        "fail_closed_triggered": fail_closed,
        "fail_closed_reason": reason,
        "confidence_tier": tier,
        "signals": signals,
        "evidence_score": score,
        "deterministic_signal_count": det_count,
        "hard_gates_triggered": gates,
    }
