# post_locator_rerank: 결정론 content-aware 랭커가 locator top 파일을 보정하는지.
from haco.ranking import post_locator_rerank


def test_rerank_promotes_content_match_over_locator_top():
    # file_locator 가 high confidence 로 엉뚱한 dataclass 파일을 줘도, 실제 타깃 함수를 가진
    # phase0_engine.py 를 결정론 랭커가 top 으로 올려야 한다(content miss 교정).
    snapshot = {
        "search_hints": ["compute_starvation_pressure"],
        "keyword_file_matches": ["phase0_engine.py"],
        "repo_map": [
            {"file": "wrong_dataclass.py", "symbols": [
                {"kind": "class", "name": "Config", "methods": []}]},
            {"file": "phase0_engine.py", "symbols": [
                {"kind": "function", "name": "compute_starvation_pressure",
                 "signature": "compute_starvation_pressure(food_ratio)"}]},
        ],
    }
    locator = {"files_to_read": ["wrong_dataclass.py"],
               "files_to_edit": ["wrong_dataclass.py"],
               "search_keywords": ["compute_starvation_pressure"],
               "confidence": "high"}
    out = post_locator_rerank(locator, snapshot)
    assert out["files_to_read"][0] == "phase0_engine.py"
    assert out["locator_adjusted"] is True
    assert "phase0_engine.py" in out["locator_adjust_reason"]


def test_rerank_no_evidence_keeps_locator_order():
    # content/keyword 근거가 전혀 없으면 재정렬하지 않고 locator 원본을 신뢰한다(fail-closed).
    snapshot = {"search_hints": [], "keyword_file_matches": [], "repo_map": []}
    locator = {"files_to_read": ["a.py", "b.py"], "files_to_edit": ["a.py"]}
    out = post_locator_rerank(locator, snapshot)
    assert out["files_to_read"] == ["a.py", "b.py"]
    assert out["locator_adjusted"] is False


def test_rerank_supplies_files_when_locator_empty():
    # locator 가 파일을 못 찾아도 결정론 keyword 매칭이 있으면 top 을 공급한다.
    snapshot = {"search_hints": ["compute_starvation_pressure"],
                "keyword_file_matches": ["phase0_engine.py"],
                "repo_map": [{"file": "phase0_engine.py", "symbols": [
                    {"kind": "function", "name": "compute_starvation_pressure"}]}]}
    locator = {"files_to_read": [], "files_to_edit": []}
    out = post_locator_rerank(locator, snapshot)
    assert out["files_to_read"][0] == "phase0_engine.py"
    assert out["locator_adjusted"] is True


def test_rerank_truncates_to_max_files():
    # MAX_FILES_MEDIUM(5) 초과분은 잘라 context pack pollution 을 막는다.
    files = [f"f{i}.py" for i in range(8)]
    snapshot = {"search_hints": ["f0"], "keyword_file_matches": files, "repo_map": []}
    locator = {"files_to_read": files, "files_to_edit": []}
    out = post_locator_rerank(locator, snapshot)
    assert len(out["files_to_read"]) <= 5
