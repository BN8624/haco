# locator rerank eval harness: 라벨 fixture로 rerank on/off top-1 hit-rate를 측정한다.
#
# LLM locator 품질은 unit pass/fail이 아니라 eval 지표로 다뤄야 한다. 여기서는 실제로 겪을 법한
# locator miss(엉뚱한 파일을 top으로 준 경우)를 결정론 fixture로 박제하고, post_locator_rerank가
# 정답 파일을 top으로 올리는지를 baseline(raw locator)과 비교한다. LLM API를 때리지 않으므로
# 결정론적이고 CI에 넣을 수 있다. 수동 측정은 `python tests/test_eval_locator.py`.
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # 단독 실행 시 haco 임포트

from haco.config import load_config  # noqa: E402
from haco.ranking import post_locator_rerank  # noqa: E402
from haco.scanner import scan_project  # noqa: E402

# 각 케이스: files(합성 repo) + task(scanner 키워드 산출) + locator(박제된 LLM 출력) + gold(정답 파일).
# miss=True 는 "baseline(raw locator)이 틀리게 잡은" 케이스 — rerank의 교정 가치를 증명한다.
CASES: list[dict] = [
    {
        "name": "content_miss_wrong_file_top",
        "files": {
            "phase0_engine.py":
                "def compute_starvation_pressure(food_ratio, has_agriculture):\n"
                "    return food_ratio * 0.5\n",
            "models.py":
                "from dataclasses import dataclass\n\n@dataclass\nclass World:\n"
                "    width: int\n    height: int\n",
        },
        "task": "compute_starvation_pressure 함수의 기아 압력 계산 로직 수정",
        "locator": {"files_to_read": ["models.py"], "files_to_edit": ["models.py"],
                    "search_keywords": ["starvation", "pressure"], "confidence": "medium"},
        "gold": "phase0_engine.py",
        "miss": True,
    },
    {
        "name": "constant_table_miss",
        "files": {
            "config.py": "LINEAGE_STARVATION_RELIEF = 0.25\nRELIEF_YEARS = 5\n",
            "engine.py": "def run_sim(world):\n    return world\n",
        },
        "task": "LINEAGE_STARVATION_RELIEF 상수 값을 0.3으로 튜닝",
        "locator": {"files_to_read": ["engine.py"], "files_to_edit": ["engine.py"],
                    "search_keywords": ["relief"], "confidence": "medium"},
        "gold": "config.py",
        "miss": True,
    },
    {
        "name": "correct_pick_preserved",
        "files": {
            "calc.py": "def calculate_total(items):\n    return sum(items)\n",
            "helpers.py": "def noop():\n    return None\n",
        },
        "task": "calculate_total 함수의 합산 로직 수정",
        "locator": {"files_to_read": ["calc.py"], "files_to_edit": ["calc.py"],
                    "search_keywords": ["calculate_total"], "confidence": "high"},
        "gold": "calc.py",
        "miss": False,
    },
    {
        "name": "no_evidence_keeps_locator_order",
        "files": {
            "a.py": "def alpha():\n    return 1\n",
            "b.py": "def beta():\n    return 2\n",
        },
        "task": "전반적인 리팩터링 정리",
        "locator": {"files_to_read": ["a.py"], "files_to_edit": ["a.py"],
                    "search_keywords": [], "confidence": "low"},
        "gold": "a.py",
        "miss": False,
    },
]


def _materialize(files: dict[str, str], workdir: Path) -> None:
    for rel, content in files.items():
        p = workdir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def _eval_case(case: dict, workdir: Path, config) -> tuple[str, str]:
    """(baseline_top, reranked_top)를 반환. baseline=raw locator top, reranked=rerank 후 top."""
    _materialize(case["files"], workdir)
    snapshot = scan_project(workdir, case["task"], config)
    locator = {k: (list(v) if isinstance(v, list) else v)
               for k, v in case["locator"].items()}
    read = locator.get("files_to_read") or []
    baseline_top = read[0] if read else ""
    reranked = post_locator_rerank(locator, snapshot, config)
    rr = reranked.get("files_to_read") or []
    reranked_top = rr[0] if rr else ""
    return baseline_top, reranked_top


def run_eval(root: Path, config) -> list[dict]:
    results: list[dict] = []
    for i, case in enumerate(CASES):
        wd = root / f"case_{i}"
        wd.mkdir(parents=True, exist_ok=True)
        baseline_top, reranked_top = _eval_case(case, wd, config)
        results.append({
            "name": case["name"], "gold": case["gold"],
            "baseline_top": baseline_top, "reranked_top": reranked_top,
            "baseline_hit": baseline_top == case["gold"],
            "reranked_hit": reranked_top == case["gold"],
        })
    return results


def test_rerank_improves_and_never_regresses(tmp_path):
    config = load_config()
    results = run_eval(tmp_path, config)
    n = len(results)
    baseline_hits = sum(r["baseline_hit"] for r in results)
    reranked_hits = sum(r["reranked_hit"] for r in results)

    # 1) rerank는 baseline보다 나쁘지 않다(회귀 금지).
    assert reranked_hits >= baseline_hits
    # 2) 설계된 케이스는 rerank가 전부 정답 top을 잡아야 한다.
    assert reranked_hits == n, [r for r in results if not r["reranked_hit"]]
    # 3) baseline엔 miss가 있어야 eval이 의미 있다(rerank의 교정 가치 증명).
    assert baseline_hits < n
    # 4) miss로 라벨된 케이스는 baseline이 틀리고 rerank가 고쳐야 한다.
    for r, case in zip(results, CASES):
        if case["miss"]:
            assert not r["baseline_hit"] and r["reranked_hit"], r


def main() -> None:
    config = load_config()
    root = Path(tempfile.mkdtemp(prefix="haco_eval_"))
    results = run_eval(root, config)
    n = len(results)
    b = sum(r["baseline_hit"] for r in results)
    rr = sum(r["reranked_hit"] for r in results)
    print(f"\nLocator rerank eval — {n} cases\n" + "-" * 68)
    print(f"{'case':32} {'gold':16} base rerank")
    for r in results:
        print(f"{r['name']:32} {r['gold']:16} "
              f"{'HIT ' if r['baseline_hit'] else 'miss':4} "
              f"{'HIT' if r['reranked_hit'] else 'miss'}")
    print("-" * 68)
    print(f"top-1 hit-rate: baseline {b}/{n} ({b / n:.0%})  →  "
          f"rerank {rr}/{n} ({rr / n:.0%})")


if __name__ == "__main__":
    main()
