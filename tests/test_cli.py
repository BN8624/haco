# cli: doctor/show/run/run --task-file 실행.
from haco.cli import main


def test_doctor_runs(capsys):
    rc = main(["doctor"])
    out = capsys.readouterr().out
    assert "HACO doctor" in out
    assert rc in (0, 1)


def test_run_with_task(sample_project, capsys):
    rc = main(["run", "--project", str(sample_project),
               "--task", "Add subtract function"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "execution_brief" in out


def test_run_with_task_file(sample_project, tmp_path, capsys):
    tf = tmp_path / "task.md"
    tf.write_text("Refactor the Calculator class", encoding="utf-8")
    rc = main(["run", "--project", str(sample_project), "--task-file", str(tf)])
    assert rc == 0


def test_preflight_then_show(sample_project, capsys):
    main(["preflight", "--project", str(sample_project),
          "--task", "Add subtract"])
    capsys.readouterr()
    latest = sample_project / ".haco" / "runs" / "latest"
    rc = main(["show", str(latest)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "HACO run" in out
    assert "candidates" in out


def test_no_task_errors(sample_project):
    import pytest
    with pytest.raises(SystemExit):
        main(["preflight", "--project", str(sample_project)])
