<!-- 다른 프로젝트의 AI 코딩 에이전트가 HACO를 도구로 호출하는 법을 읽는 사용 설명서. -->
# HACO — Harness for Agent Cost Optimization

**HACO is a CLI harness that a coding agent calls before doing expensive work.**
It is *not* a human app and *not* an autonomous coding agent. It prepares focused
context, task packets, candidates, and postflight records so the main coding agent
reads less, searches less, and spends fewer expensive tokens.

> **Audience of this file:** an AI coding agent working in *another* project that
> wants to use HACO as a tool. It is not a human-facing project overview.

Core order:

```
Cheap deterministic tools first → free/low-cost workers second → expensive main-agent reasoning last.
```

Fail-closed: when confidence is low, HACO output gets **shorter**, not longer. It
would rather help less than hand the main agent polluted context with false confidence.

---

## Install

```bash
pip install -e .            # exposes the `haco` command; or use `python -m haco`
pip install -e .[google]    # optional: google/gemma provider
```

Requires Python 3.10+. Default provider is `mock` (deterministic, no network).

---

## Using HACO from another project

When the user says "use haco" / "하코 사용", or the task is non-trivial repository
work (multi-file edits, debugging, refactor, test-failure analysis, review):

1. **Long or multiline task?** Write it to a file first (avoids shell arg limits):

   ```bash
   # .haco/task_input.md   ← put the full task here
   ```

2. **Run preflight** (from the target project root):

   ```bash
   python -m haco preflight --project . --task "<task>"
   python -m haco preflight --project . --task-file .haco/task_input.md
   ```

   Profiles: `--profile quick | standard | deep` (default `standard`).
   `quick` = no candidates; `deep` = multiple patch candidates.

3. **Read the outputs, in this order:**

   ```
   .haco/runs/latest/context_pack.md      ← focused excerpts; read this FIRST
   .haco/runs/latest/task_packet.json     ← task type, files, confidence, status
   .haco/runs/latest/execution_brief.md   ← what to do
   .haco/runs/latest/candidates/          ← advisory patch/test candidates
   ```

4. **Apply changes yourself.** HACO does not edit target files. Candidates are
   *advisory* — adapt them, do not apply blindly.

5. **After work, run postflight:**

   ```bash
   python -m haco postflight --run .haco/runs/latest --project .
   ```

### Key signals

- **`haco_status`** — `ready` or `skip_to_main_agent`. If `skip_to_main_agent`,
  HACO was not confident; proceed with normal **bounded exploration** and record why.
- **`confidence_tier`** — `high | medium | low | none` from deterministic evidence
  (path/range/symbol/keyword signals), not LLM self-report.
- **`locator_adjusted`** — a deterministic ranker overrode the LLM's top file pick;
  `locator_adjust_reason` says why.
- **`context_pack.md`** — deterministic focused excerpts (symbol ranges / markdown
  sections / keyword windows), budget-bounded. Read it before opening whole files.

Other commands: `python -m haco doctor` (environment check),
`haco run` (preflight + point to brief), `haco show <run>`, `haco init`.

---

## Paste this into the target project's `CLAUDE.md` / `AGENTS.md`

```md
## HACO Usage Rule

When the user says "use haco", "하코 사용", or asks to reduce expensive model usage:

1. If the task is long or multiline, write it to `.haco/task_input.md` first.
2. Run one of:
   - `python -m haco preflight --project . --task "<user task>"`
   - `python -m haco preflight --project . --task-file .haco/task_input.md`
3. Read `.haco/runs/latest/context_pack.md` first, then `task_packet.json` and
   `execution_brief.md`, then inspect `.haco/runs/latest/candidates/`.
4. If `haco_status=skip_to_main_agent`, do bounded exploration and record the reason.
5. Prefer adapting HACO candidates over writing a patch from scratch; never apply blindly.
6. After work, run `python -m haco postflight --run .haco/runs/latest --project .`.
7. Do not commit `.haco/`.
```

---

## Providers

- **mock** (default): deterministic, offline. Good for CI and dry runs.
- **google** (gemma): set API keys in `.env` (multiple keys rotate on rate limit).
  Worker-level fallback keeps the flow going when a single call fails.

---

## Limitations

- `primary_language` / `test_frameworks` detection is best-effort and can be wrong.
- Candidates are a review set for the main agent, not guaranteed-correct patches.
- Confidence thresholds are pollution-prevention gates, not correctness guarantees.

References: Aider (repo map, search/replace edits), SWE-agent (bounded agent-computer
interface), AlphaCodium (code generation as multi-stage flow).
