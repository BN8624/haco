# HACO 제작용 임시 bootstrap. Gemma 11-key 검토 worker pool 골격 (mock + google).
from __future__ import annotations

from pathlib import Path

from haco.config import Config
from haco.model_client import ModelProvider, get_provider
from haco.utils import encode_context_block, read_text, write_json, write_text

BOOTSTRAP_PROMPT_DIR = Path(__file__).resolve().parent.parent / "bootstrap" / "prompts"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "bootstrap" / "outputs"

WORKER_NAMES = [f"worker_{i:02d}" for i in range(1, 12)]


def _load_bootstrap_prompt(name: str) -> str:
    path = BOOTSTRAP_PROMPT_DIR / f"{name}_*.md"
    matches = list(BOOTSTRAP_PROMPT_DIR.glob(f"{name}_*.md"))
    if matches:
        return matches[0].read_text(encoding="utf-8")
    return f"You are HACO bootstrap reviewer {name}. Review the contract. Respond in JSON."


def _ensure_no_key_leak(data: dict) -> None:
    """출력에 API key 값이 섞이지 않았는지 방어적으로 확인한다."""
    import os
    secrets = [v for k, v in os.environ.items()
               if "API_KEY" in k and v]
    blob = str(data)
    for s in secrets:
        if s and s in blob:
            raise RuntimeError("API key value detected in bootstrap output; aborting.")


def run_bootstrap(*, contract_path: Path, config: Config,
                  provider: ModelProvider | None = None,
                  output_dir: Path | None = None) -> dict:
    provider = provider or get_provider(config)
    output_dir = Path(output_dir or DEFAULT_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    contract = read_text(contract_path)
    write_text(output_dir / "input_contract.md", contract[:200])  # 발췌만 보관

    results: list[dict] = []
    for name in WORKER_NAMES:
        template = _load_bootstrap_prompt(name)
        # 컨텍스트에는 절대 key를 넣지 않는다. contract 발췌만.
        context = {"role": name, "contract_excerpt": contract[:4000]}
        prompt = template + "\n\n" + encode_context_block(context)
        try:
            out = provider.generate_json(prompt, name)
        except Exception as e:  # noqa: BLE001
            out = {"worker": name, "findings": [],
                   "reason": f"fallback: {type(e).__name__}", "_haco_fallback": True}
        out.setdefault("worker", name)
        _ensure_no_key_leak(out)
        write_json(output_dir / f"{name}.json", out)
        results.append(out)

    # aggregate.md (중복 제거 요약)
    lines = ["# HACO Bootstrap Aggregate", "",
             f"Provider: {provider.name}", f"Workers: {len(results)}", ""]
    seen: set[str] = set()
    for r in results:
        lines.append(f"## {r.get('worker')}")
        reason = r.get("reason", "")
        if reason and reason not in seen:
            seen.add(reason)
            lines.append(f"- {reason}")
        for f in r.get("findings", []) or []:
            f_str = str(f)
            if f_str not in seen:
                seen.add(f_str)
                lines.append(f"- {f_str}")
        lines.append("")
    write_text(output_dir / "aggregate.md", "\n".join(lines))

    return {
        "output_dir": str(output_dir),
        "workers": len(results),
        "aggregate": str(output_dir / "aggregate.md"),
    }
