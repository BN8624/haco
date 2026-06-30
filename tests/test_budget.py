# budget: char 계산, structural trimming, valid JSON 유지, truncation_notes.
import json

from haco.budget import char_count, trim_repo_map, trim_snapshot, trim_text


def test_char_count():
    assert char_count("abc") == 3
    assert char_count({"a": "bc"}) == len(json.dumps({"a": "bc"}))


def test_trim_snapshot_keeps_valid_json():
    snap = {
        "project_path": "/x", "primary_language": "python",
        "project_type": "python_package", "test_frameworks": ["pytest"],
        "file_paths_sample": [f"file_{i}.py" for i in range(500)],
        "tree_preview": [f"line {i}" for i in range(300)],
        "repo_map": [{"file": f"f{i}.py", "symbols": [
            {"kind": "function", "name": f"fn{i}", "signature": f"fn{i}()",
             "docstring_preview": "x" * 100}]} for i in range(80)],
        "keyword_file_matches": [], "git_status": "", "readme_preview": "",
        "recent_files": [], "truncation_notes": [],
    }
    trimmed = trim_snapshot(snap, 1500)
    json.dumps(trimmed)  # 깨지지 않아야 함
    assert trimmed["truncation_applied"] is True
    assert trimmed["truncation_notes"]
    assert char_count(trimmed) <= 1500 * 3  # fallback 포함 충분히 작아짐


def test_trim_repo_map_structural():
    rm = [{"file": f"f{i}.py", "symbols": [
        {"kind": "function", "name": f"fn{j}", "signature": f"fn{j}()",
         "docstring_preview": "doc " * 30} for j in range(10)]} for i in range(20)]
    trimmed, notes = trim_repo_map(rm, 500)
    assert char_count(trimmed) <= 500
    json.dumps(trimmed)
    assert notes


def test_trim_text_balances_code_fence():
    text = "intro\n```python\n" + "x = 1\n" * 200 + "```\n"
    trimmed, notes = trim_text(text, 200, "brief")
    assert trimmed.count("```") % 2 == 0
    assert notes
