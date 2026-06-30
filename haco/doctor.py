# doctor: HACO 환경 점검. 각 항목을 검사하고 사람이 읽을 수 있게 출력한다.
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from haco.config import load_config, load_env
from haco.model_client import MockProvider, get_provider
from haco.schemas import validate_worker_output
from haco.workers import PROMPT_DIR, build_prompt
from haco.budget import trim_snapshot

BOOTSTRAP_PROMPT_DIR = Path(__file__).resolve().parent.parent / "bootstrap" / "prompts"


def run_doctor(project_path: Path | None = None) -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    project_path = Path(project_path or Path.cwd())
    load_env(project_path)

    # Python version
    v = sys.version_info
    checks.append(("python_version", v >= (3, 10), f"{v.major}.{v.minor}.{v.micro}"))

    # package import
    try:
        import haco  # noqa: F401
        checks.append(("package_import", True, "haco importable"))
    except Exception as e:  # noqa: BLE001
        checks.append(("package_import", False, str(e)))

    # config load
    try:
        config = load_config(project_path=project_path)
        checks.append(("config_load", True, f"provider={config.provider}"))
    except Exception as e:  # noqa: BLE001
        config = None
        checks.append(("config_load", False, str(e)))

    # runs dir writable
    try:
        runs = project_path / ".haco" / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        testfile = runs / ".write_test"
        testfile.write_text("ok", encoding="utf-8")
        testfile.unlink()
        checks.append(("runs_dir_writable", True, str(runs)))
    except Exception as e:  # noqa: BLE001
        checks.append(("runs_dir_writable", False, str(e)))

    # mock provider
    try:
        mp = MockProvider()
        out = mp.generate_json(build_prompt("task_router", {"task": "test"}),
                               "task_router")
        ok = out.get("worker") == "task_router"
        checks.append(("mock_provider", ok, "deterministic output ok"))
    except Exception as e:  # noqa: BLE001
        checks.append(("mock_provider", False, str(e)))

    # google provider configured?
    if config:
        try:
            gp = get_provider(load_config(project_path=project_path))
            if config.provider == "google":
                slots = getattr(gp, "key_slots", [])
                checks.append(("google_provider", bool(slots),
                               f"{len(slots)} key slot(s) found"))
            else:
                # 키 존재 여부만 정보성으로
                from haco.model_client import GoogleProvider
                slots = GoogleProvider._discover_key_slots(config)
                checks.append(("google_provider", True,
                               f"provider=mock; {len(slots)} google key slot(s) available"))
        except Exception as e:  # noqa: BLE001
            checks.append(("google_provider", False, str(e)))

    # prompts exist
    prompt_files = list(PROMPT_DIR.glob("*.md")) if PROMPT_DIR.exists() else []
    checks.append(("prompts_exist", len(prompt_files) >= 8,
                   f"{len(prompt_files)} worker prompts in {PROMPT_DIR}"))

    # pydantic schema validation
    try:
        validate_worker_output("task_router", {"worker": "task_router"})
        checks.append(("schema_validation", True, "pydantic ok"))
    except Exception as e:  # noqa: BLE001
        checks.append(("schema_validation", False, str(e)))

    # repo_map path
    try:
        from haco.repo_map import extract_python_symbols
        syms = extract_python_symbols("def f(x):\n    'doc'\n    return x\n")
        checks.append(("repo_map", any(s.get("name") == "f" for s in syms),
                       "python ast extraction ok"))
    except Exception as e:  # noqa: BLE001
        checks.append(("repo_map", False, str(e)))

    # budget trimming
    try:
        snap = {"project_path": "x", "primary_language": "python",
                "project_type": "generic", "test_frameworks": [],
                "file_paths_sample": ["a"] * 1000, "repo_map": [],
                "tree_preview": [], "truncation_notes": []}
        trimmed = trim_snapshot(snap, 200)
        import json
        json.dumps(trimmed)
        checks.append(("budget_trimming", True, "structural trimming ok"))
    except Exception as e:  # noqa: BLE001
        checks.append(("budget_trimming", False, str(e)))

    # bootstrap prompts
    bp = list(BOOTSTRAP_PROMPT_DIR.glob("*.md")) if BOOTSTRAP_PROMPT_DIR.exists() else []
    checks.append(("bootstrap_prompts", len(bp) >= 11,
                   f"{len(bp)} bootstrap prompts"))

    return checks


def print_doctor(checks: list[tuple[str, bool, str]]) -> bool:
    all_ok = True
    print("HACO doctor\n")
    for name, ok, detail in checks:
        mark = "OK  " if ok else "FAIL"
        if not ok:
            all_ok = False
        print(f"[{mark}] {name}: {detail}")
    print()
    print("All checks passed." if all_ok else "Some checks failed.")
    return all_ok
