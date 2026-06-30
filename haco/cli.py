# HACO CLI 진입점. init/doctor/preflight/run/show/postflight/bootstrap 서브커맨드.
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from haco.config import load_config, load_env
from haco.model_client import get_provider
from haco.run_store import resolve_run
from haco.utils import read_json, read_text


def _resolve_task(args) -> str:
    """--task-file 우선. 둘 다 없으면 에러."""
    if getattr(args, "task_file", None):
        path = Path(args.task_file)
        if not path.exists():
            _die(f"task file not found: {path}")
        if getattr(args, "task", None):
            print("haco: both --task and --task-file given; using --task-file.",
                  file=sys.stderr)
        return read_text(path)
    if getattr(args, "task", None):
        return args.task
    _die("no task provided: use --task \"...\" or --task-file <path>")


def _die(msg: str, code: int = 2) -> "None":
    print(f"haco: error: {msg}", file=sys.stderr)
    raise SystemExit(code)


def _common_config(args):
    project_path = Path(getattr(args, "project", None) or ".").resolve()
    load_env(project_path)
    config = load_config(getattr(args, "config", None), project_path=project_path)
    return project_path, config


def cmd_init(args) -> int:
    project_path = Path(getattr(args, "project", None) or ".").resolve()
    haco_dir = project_path / ".haco"
    (haco_dir / "runs").mkdir(parents=True, exist_ok=True)
    cfg = project_path / "config.yaml"
    if not cfg.exists():
        example = Path(__file__).resolve().parent.parent / "config.example.yaml"
        if example.exists():
            cfg.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"created {cfg}")
        else:
            print("config.example.yaml not found; skipped config.yaml")
    else:
        print(f"{cfg} already exists; left unchanged")
    print(f"initialized HACO in {haco_dir}")
    return 0


def cmd_doctor(args) -> int:
    from haco.doctor import print_doctor, run_doctor
    project_path = Path(getattr(args, "project", None) or ".").resolve()
    checks = run_doctor(project_path)
    ok = print_doctor(checks)
    return 0 if ok else 1


def cmd_preflight(args) -> int:
    from haco.preflight import run_preflight
    task = _resolve_task(args)
    project_path, config = _common_config(args)
    provider = get_provider(config)
    profile = args.profile or config.profiles.get("default", "standard")
    result = run_preflight(project_path=project_path, task=task, profile=profile,
                           config=config, provider=provider)
    print(f"haco preflight done (status={result['haco_status']})")
    print(f"  run:             {result['run_path']}")
    print(f"  task_packet:     {result['task_packet']}")
    print(f"  execution_brief: {result['execution_brief']}")
    print(f"  candidates:      {result['candidates']}")
    print(f"  metrics:         {result['metrics']}")
    return 0


def cmd_run(args) -> int:
    from haco.preflight import run_preflight
    task = _resolve_task(args)
    project_path, config = _common_config(args)
    provider = get_provider(config)
    profile = getattr(args, "profile", None) or config.profiles.get("default", "standard")
    result = run_preflight(project_path=project_path, task=task, profile=profile,
                           config=config, provider=provider)
    print("haco run complete.")
    print(f"  task_packet:     {result['task_packet']}")
    print(f"  execution_brief: {result['execution_brief']}")
    print(f"  candidates:      {result['candidates']}")
    print()
    print("Main coding agent: read execution_brief.md and proceed.")
    return 0


def cmd_postflight(args) -> int:
    from haco.postflight import run_postflight
    project_path = Path(getattr(args, "project", None) or ".").resolve()
    run_path = resolve_run(args.run, project_path)
    if not Path(run_path).exists():
        _die(f"run path not found: {args.run}")
    load_env(project_path)
    config = load_config(getattr(args, "config", None), project_path=project_path)
    provider = get_provider(config)
    result = run_postflight(run_path=run_path, project_path=project_path,
                            config=config, provider=provider)
    print("haco postflight done.")
    print(f"  report:            {result['report']}")
    print(f"  postflight_packet: {result['postflight_packet']}")
    if result["missing_validation"]:
        print("  warning: no HACO Validation section found in execution_result.md")
    if result["fix_candidates"]:
        print(f"  fix candidates:    {', '.join(result['fix_candidates'])}")
    return 0


def cmd_show(args) -> int:
    project_path = Path(getattr(args, "project", None) or ".").resolve()
    run_path = Path(resolve_run(args.run, project_path))
    if not run_path.exists():
        _die(f"run path not found: {args.run}")
    packet = read_json(run_path / "task_packet.json", default={}) or {}
    metrics = read_json(run_path / "metrics.json", default={}) or {}
    snapshot = read_json(run_path / "project_snapshot.json", default={}) or {}
    cs = packet.get("candidate_summary", {})

    print(f"HACO run: {run_path}")
    print(f"  input:        {read_text(run_path / 'input.md').strip()[:80]!r}")
    print(f"  haco_status:  {packet.get('haco_status', '?')}"
          f"  skip_reason={packet.get('skip_reason', '') or '-'}")
    print(f"  task_type:    {packet.get('task_type', '?')}  risk={packet.get('risk', '?')}")
    print(f"  files_to_read:{packet.get('files_to_read', [])}")
    print(f"  repo_map:     status={snapshot.get('repo_map_status', '?')} "
          f"files={len(snapshot.get('repo_map', []))}")
    print(f"  candidates:   generated={cs.get('generated', 0)} "
          f"accepted={cs.get('accepted', 0)} masked={cs.get('masked', 0)} "
          f"rejected={cs.get('rejected', 0)}")
    cdir = run_path / "candidates"
    if cdir.exists():
        for c in sorted(cdir.iterdir()):
            if c.is_dir():
                print(f"    - {c.name}")
    print("  worker outputs:")
    wdir = run_path / "worker_outputs"
    if wdir.exists():
        for w in sorted(wdir.glob("*.json")):
            print(f"    - {w.name}")
    print(f"  metrics:      brief_chars={metrics.get('execution_brief_chars', 0)} "
          f"snapshot_chars={metrics.get('project_snapshot_chars', 0)} "
          f"wall={metrics.get('preflight_wall_time_seconds', 0)}s")
    pf = read_json(run_path / "postflight_packet.json", default=None)
    if pf:
        eff = pf.get("haco_effectiveness", {})
        print(f"  effectiveness: used_haco={eff.get('main_agent_used_haco')} "
              f"skip={eff.get('skip_to_main_agent')}")
    report = run_path / "report.md"
    print(f"  report:       {'present' if report.exists() else 'absent'}")
    return 0


def cmd_bootstrap(args) -> int:
    from haco.bootstrap import run_bootstrap
    project_path, config = _common_config(args)
    contract = Path(args.contract) if getattr(args, "contract", None) else \
        (project_path / "HACO.md")
    provider = get_provider(config)
    result = run_bootstrap(contract_path=contract, config=config, provider=provider)
    print(f"bootstrap done: {result['workers']} workers")
    print(f"  output_dir: {result['output_dir']}")
    print(f"  aggregate:  {result['aggregate']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="haco",
                                description="Harness for Agent Cost Optimization")
    sub = p.add_subparsers(dest="command", required=True)

    def add_common(sp):
        sp.add_argument("--project", default=".", help="target project path")
        sp.add_argument("--config", default=None, help="config.yaml path")

    sp = sub.add_parser("init", help="initialize HACO in a project")
    sp.add_argument("--project", default=".")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("doctor", help="check HACO environment")
    sp.add_argument("--project", default=".")
    sp.set_defaults(func=cmd_doctor)

    sp = sub.add_parser("preflight", help="prepare task packet and candidates")
    add_common(sp)
    sp.add_argument("--task", default=None)
    sp.add_argument("--task-file", dest="task_file", default=None)
    sp.add_argument("--profile", default=None, choices=["quick", "standard", "deep"])
    sp.set_defaults(func=cmd_preflight)

    sp = sub.add_parser("run", help="preflight then point the agent to the brief")
    add_common(sp)
    sp.add_argument("--task", default=None)
    sp.add_argument("--task-file", dest="task_file", default=None)
    sp.add_argument("--profile", default=None, choices=["quick", "standard", "deep"])
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("postflight", help="summarize results after agent work")
    sp.add_argument("--run", required=True)
    sp.add_argument("--project", default=".")
    sp.add_argument("--config", default=None)
    sp.set_defaults(func=cmd_postflight)

    sp = sub.add_parser("show", help="show a run summary")
    sp.add_argument("run")
    sp.add_argument("--project", default=".")
    sp.set_defaults(func=cmd_show)

    sp = sub.add_parser("bootstrap", help="run the 11-key design review (mock/google)")
    add_common(sp)
    sp.add_argument("--contract", default=None)
    sp.set_defaults(func=cmd_bootstrap)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
