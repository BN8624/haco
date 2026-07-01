# context_pack: 결정론적 focused excerpt 생성, budget/fail-closed, preflight 통합.
import json
from pathlib import Path

from haco.context_pack import build_context_pack
from haco.model_client import MockProvider
from haco.preflight import run_preflight
from haco.schemas import TaskPacket


def _run(project, task, config, profile="standard"):
    return run_preflight(project_path=project, task=task, profile=profile,
                         config=config, provider=MockProvider())


def test_build_context_pack_symbol_excerpt(sample_project, config):
    snapshot = {"repo_map": [{"file": "pkg/calc.py", "symbols": [
        {"kind": "function", "name": "add", "signature": "add(a, b)",
         "line_start": 1, "line_end": 3},
    ]}]}
    packet = TaskPacket(files_to_read=["pkg/calc.py"], search_keywords=["add"])
    md, js = build_context_pack(project_path=sample_project, snapshot=snapshot,
                                packet=packet, config=config)
    assert js["status"] == "ready"
    assert js["files"]
    entry = js["files"][0]
    assert entry["file"] == "pkg/calc.py"
    assert entry["line_start"] == 1 and entry["line_end"] == 3
    assert entry["symbol"] == "add"
    assert "def add" in md  # 실제 소스 excerpt가 들어간다


def test_symbol_name_match_beats_signature_match(sample_project, config):
    # Intent: task가 지목한 함수명(정확매칭)이 무관 함수의 시그니처 substring 매칭보다 우선.
    # create_world는 signature에 rng를, target은 이름 자체가 키워드. target이 선택돼야 한다.
    (sample_project / "eng.py").write_text(
        "def create_world(width, height, rng):\n    return 1\n\n"
        "def compute_starvation_pressure(food_ratio, has_agriculture):\n    return 2\n",
        encoding="utf-8")
    snapshot = {"repo_map": [{"file": "eng.py", "symbols": [
        {"kind": "function", "name": "create_world",
         "signature": "create_world(width, height, rng)", "line_start": 1, "line_end": 2},
        {"kind": "function", "name": "compute_starvation_pressure",
         "signature": "compute_starvation_pressure(food_ratio, has_agriculture)",
         "line_start": 4, "line_end": 5},
    ]}]}
    packet = TaskPacket(files_to_read=["eng.py"],
                        search_keywords=["compute_starvation_pressure", "rng"])
    md, js = build_context_pack(project_path=sample_project, snapshot=snapshot,
                                packet=packet, config=config)
    syms = [f["symbol"] for f in js["files"]]
    assert "compute_starvation_pressure" in syms
    assert syms[0] == "compute_starvation_pressure"  # 정확매칭이 맨 앞


def test_context_pack_uses_snapshot_search_hints(sample_project, config):
    # locator가 search_keywords를 잘라도 snapshot.search_hints의 식별자로 심볼을 좁힌다.
    snapshot = {"search_hints": ["compute_starvation_pressure"], "repo_map": [
        {"file": "pkg/calc.py", "symbols": [
            {"kind": "function", "name": "add", "line_start": 1, "line_end": 3}]}]}
    (sample_project / "pkg" / "eng.py").write_text(
        "def compute_starvation_pressure(x):\n    return x\n", encoding="utf-8")
    snapshot["repo_map"].append({"file": "pkg/eng.py", "symbols": [
        {"kind": "function", "name": "compute_starvation_pressure",
         "signature": "compute_starvation_pressure(x)", "line_start": 1, "line_end": 2}]})
    packet = TaskPacket(files_to_read=["pkg/eng.py"], search_keywords=[])  # locator가 다 잘림
    md, js = build_context_pack(project_path=sample_project, snapshot=snapshot,
                                packet=packet, config=config)
    assert any("matched the task" in f["reason"] for f in js["files"])


def test_adaptive_symbols_for_many_exact_matches(sample_project, config):
    # exact_name 매칭 심볼이 5개면 기본 상한 3을 넘어 excerpt 를 허용한다(상수 테이블 변경 등).
    (sample_project / "consts.py").write_text(
        "AAA = 1\nBBB = 2\nCCC = 3\nDDD = 4\nEEE = 5\nFFF = 6\n", encoding="utf-8")
    symbols = [{"kind": "constant", "name": n, "signature": f"{n} = ",
                "line_start": i + 1, "line_end": i + 1}
               for i, n in enumerate(["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"])]
    snapshot = {"repo_map": [{"file": "consts.py", "symbols": symbols}]}
    packet = TaskPacket(files_to_read=["consts.py"],
                        search_keywords=["aaa", "bbb", "ccc", "ddd", "eee"])
    md, js = build_context_pack(project_path=sample_project, snapshot=snapshot,
                                packet=packet, config=config)
    entries = [f for f in js["files"] if f["file"] == "consts.py"]
    assert len(entries) > 3  # 기본 상한 3 초과 허용
    assert all(f.get("match_tier") == "exact_name" for f in entries[:5])


def test_build_context_pack_fail_closed_on_skip(sample_project, config):
    packet = TaskPacket(haco_status="skip_to_main_agent",
                        files_to_read=["pkg/calc.py"])
    md, js = build_context_pack(project_path=sample_project, snapshot={},
                                packet=packet, config=config)
    assert js["status"] == "skipped"
    assert js["files"] == []          # skip이면 excerpt를 만들지 않는다
    assert "bounded exploration" in md.lower()


def test_build_context_pack_missing_file_noted(sample_project, config):
    packet = TaskPacket(files_to_read=["does_not_exist.py"])
    md, js = build_context_pack(project_path=sample_project, snapshot={},
                                packet=packet, config=config)
    assert js["files"] == []
    assert any("not found" in o for o in js["omitted"])


def test_preflight_writes_context_pack(sample_project, config):
    result = _run(sample_project, "Add a subtract function to calc.py", config)
    run = Path(result["run_path"])
    assert (run / "context_pack.md").exists()
    assert (run / "context_pack.json").exists()
    js = json.loads((run / "context_pack.json").read_text(encoding="utf-8"))
    assert "status" in js and "budget" in js
    assert result["context_pack"].endswith("context_pack.md")


def test_context_pack_deterministic(sample_project, config):
    r1 = _run(sample_project, "Add subtract function to calc.py", config)
    r2 = _run(sample_project, "Add subtract function to calc.py", config)
    a = (Path(r1["run_path"]) / "context_pack.md").read_text(encoding="utf-8")
    b = (Path(r2["run_path"]) / "context_pack.md").read_text(encoding="utf-8")
    assert a == b
