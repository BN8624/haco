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
