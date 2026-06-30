# run 디렉터리(.haco/runs/<timestamp>) 생성과 latest 해석을 담당한다.
from __future__ import annotations

from pathlib import Path

from haco.utils import now_run_id, read_text, write_text

LATEST_MARKER = "latest_marker.txt"


def runs_root(project_path: Path, runs_dir: str = ".haco/runs") -> Path:
    return Path(project_path) / runs_dir


def create_run(project_path: Path, runs_dir: str = ".haco/runs",
               run_id: str | None = None) -> Path:
    """새 run 디렉터리를 만들고 latest를 갱신한다. run 경로를 반환."""
    root = runs_root(project_path, runs_dir)
    root.mkdir(parents=True, exist_ok=True)
    rid = run_id or now_run_id()
    run_path = root / rid
    # 동일 초에 두 번 만들면 충돌 → suffix
    suffix = 1
    while run_path.exists():
        run_path = root / f"{rid}_{suffix}"
        suffix += 1
    (run_path / "worker_outputs").mkdir(parents=True, exist_ok=True)
    (run_path / "candidates").mkdir(parents=True, exist_ok=True)
    _update_latest(root, run_path)
    return run_path


def _clear_latest(latest: Path) -> None:
    if latest.is_symlink():
        latest.unlink()
        return
    if not latest.exists():
        return
    if latest.is_file():
        latest.unlink()
        return
    # 디렉터리/junction
    try:
        latest.rmdir()  # junction 또는 빈 marker dir
    except OSError:
        import shutil
        shutil.rmtree(latest, ignore_errors=True)


def _try_junction(latest: Path, run_path: Path) -> bool:
    """Windows에서 권한 없이 동작하는 디렉터리 junction 생성 시도."""
    import os
    if os.name != "nt":
        return False
    import subprocess
    try:
        # 출력을 디코드하지 않는다(한국어 콘솔 인코딩으로 reader 스레드가 깨질 수 있음).
        r = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(latest), str(run_path)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        return r.returncode == 0 and latest.exists()
    except Exception:
        return False


def _update_latest(root: Path, run_path: Path) -> None:
    """latest 갱신: symlink → (Windows) junction → marker 디렉터리 순으로 폴백.

    symlink/junction은 `.haco/runs/latest/<file>` 직접 읽기를 지원한다.
    marker 디렉터리는 최후 폴백이며 resolve_run으로만 해석된다.
    """
    latest = root / "latest"
    _clear_latest(latest)
    # 1) symlink
    try:
        latest.symlink_to(run_path.name, target_is_directory=True)
        return
    except (OSError, NotImplementedError):
        pass
    # 2) Windows junction (권한 불필요, 직접 경로 읽기 가능)
    if _try_junction(latest, run_path):
        return
    # 3) marker 디렉터리
    latest.mkdir(parents=True, exist_ok=True)
    write_text(latest / LATEST_MARKER, run_path.name)


def resolve_run(run_arg: str | Path) -> Path:
    """show/postflight가 받은 run 경로를 실제 run 디렉터리로 해석한다.

    - symlink면 따라간다.
    - marker 디렉터리면 marker가 가리키는 형제 디렉터리로 해석한다.
    """
    p = Path(run_arg)
    if p.is_symlink():
        return p.resolve()
    if p.is_dir():
        marker = p / LATEST_MARKER
        if marker.exists():
            target_name = read_text(marker).strip()
            if target_name:
                resolved = p.parent / target_name
                if resolved.exists():
                    return resolved
        return p
    return p
