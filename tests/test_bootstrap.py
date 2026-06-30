# bootstrap: prompt 존재, mock worker outputs, aggregate, API key 미노출.
from haco.bootstrap import (BOOTSTRAP_PROMPT_DIR, WORKER_NAMES, run_bootstrap)
from haco.model_client import MockProvider


def test_bootstrap_prompts_exist():
    files = list(BOOTSTRAP_PROMPT_DIR.glob("*.md"))
    assert len(files) >= 11


def test_bootstrap_mock_outputs(tmp_path, config):
    contract = tmp_path / "HACO.md"
    contract.write_text("# HACO contract\nSome rules.\n", encoding="utf-8")
    out_dir = tmp_path / "bootstrap_out"
    result = run_bootstrap(contract_path=contract, config=config,
                           provider=MockProvider(), output_dir=out_dir)
    assert result["workers"] == len(WORKER_NAMES)
    assert (out_dir / "aggregate.md").exists()
    for name in WORKER_NAMES:
        assert (out_dir / f"{name}.json").exists()


def test_bootstrap_no_key_leak(tmp_path, config, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY_1", "secret-key-value-123")
    contract = tmp_path / "HACO.md"
    contract.write_text("contract", encoding="utf-8")
    out_dir = tmp_path / "bo"
    run_bootstrap(contract_path=contract, config=config,
                  provider=MockProvider(), output_dir=out_dir)
    for f in out_dir.glob("*.json"):
        assert "secret-key-value-123" not in f.read_text(encoding="utf-8")
    assert "secret-key-value-123" not in (out_dir / "aggregate.md").read_text(
        encoding="utf-8")
