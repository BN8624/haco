# HACO — Harness for Agent Cost Optimization

HACO is a **CLI harness that coding agents call before doing expensive work**. It
is not an app you use directly. When you tell Claude Code or Codex "use haco",
the agent runs HACO, which uses a cheap Gemma worker pool to scan the project,
compress context, locate files, and generate coding candidates — so the expensive
main agent reads less and decides faster.

> HACO does **not** edit your project. It prepares a task packet and candidate
> files; the main coding agent reviews, applies, and tests.

## Why

A premium coding agent burns tokens exploring a repo from scratch. HACO front-loads
that work onto a cheap worker model and hands the main agent a small, structured
brief plus reviewable candidate packages.

## Roles

- **Gemma worker pool** (junior coders): task triage, context compression, file
  location, patch/test/fix candidate generation, doc reporting, candidate judging.
- **Claude Code / Codex** (integrator): run HACO, review candidates, apply minimal
  changes, run tests, run postflight, report.
- **HACO**: scan, repo-map, run workers, validate JSON, store candidates, build the
  execution brief, record cost-saving metrics.

## Install

```bash
pip install -e .
# requires: pydantic, python-dotenv (PyYAML, google-genai optional)
```

The required entry point is `python -m haco ...`; a `haco` console script is also
installed.

## Mock mode (default, no API key)

```bash
python -m haco doctor
python -m haco preflight --project . --task "Add a small feature"
```

`provider: mock` is deterministic and always works.

## Google provider

```bash
export HACO_PROVIDER=google     # or set provider: google in config.yaml
export GOOGLE_API_KEY=...        # single key
```

### Multiple API keys

For rate-limit resilience HACO rotates keys. It auto-detects both
`GOOGLE_API_KEY_1..N` and `GOOGLE_API_KEY_01..N` in `.env`, plus any names listed
in `config.yaml > google.api_key_envs`. On 429 / transient errors it backs off
exponentially and rotates to the next key. **Key values are never written to logs,
reports, or worker outputs** — only the slot name.

## preflight

```bash
python -m haco preflight --project . --task "..."
python -m haco preflight --project . --task-file task.md
python -m haco preflight --project . --task "..." --profile quick|standard|deep
```

If both `--task` and `--task-file` are given, **`--task-file` wins** (with a
warning). If neither is given, it errors.

### Profiles

- `quick`: router + compressor + locator + doc_reporter. No patch/test candidates.
- `standard` (default): adds patch + test candidates and candidate_judge.
- `deep`: standard, but generates multiple patch candidates and judges harder.

`docs_only` / `planning` / `research` tasks skip patch/test generation even in
`standard`.

## postflight

After the main agent writes its results into the run directory:

```bash
python -m haco postflight --run .haco/runs/latest --project .
python -m haco postflight --run latest --project .       # same, by name
python -m haco postflight --run 2026-07-01_002303 --project .  # by run ID
```

`--run` accepts a path, a run ID, or `latest`; a bare run ID or `latest` is resolved
under `<--project>/.haco/runs/`. Generates `report.md` and `postflight_packet.json`,
parsing the `HACO Validation` section from `execution_result.md`. If a failure log is
present it runs `failure_fixer` to produce a (non-applied) fix candidate. The failure
log is read from pytest-style `N failed` / `N error` counts, so a mixed summary like
`1 failed, 71 passed` is correctly detected as a failure. Script-based verifiers that
print a `status PASS` / `status FAIL` line (no pytest counts) are also recognized, and
an unrecognized log is reported as `unknown` — never silently as `failed`.

## run / show

```bash
python -m haco run --project . --task "..."   # preflight + points agent to the brief
python -m haco show .haco/runs/latest          # summarize a run
python -m haco show latest --project .         # same, resolved by name
```

`show` also takes a path, a run ID, or `latest` (run ID / `latest` resolved under
`--project`, default `.`).

## How "use haco" works (agent procedure)

When the user says "use haco" / "하코 사용":

1. If the task is long/multiline, write it to a file and use `--task-file`.
2. `python -m haco preflight --project . --task-file .haco/task_input.md`
3. Read `.haco/runs/latest/task_packet.json` and `execution_brief.md`.
4. Inspect accepted candidates in `.haco/runs/latest/candidates/`.
5. Prefer adapting HACO candidates over writing a patch from scratch.
6. Do not blindly apply `optional.diff`; prefer edit_plan/search_replace/replacement_blocks.
7. Apply changes yourself, run the recommended tests.
8. Write `execution_result.md` (with a `HACO Validation` section), `diff_summary.md`,
   and `test_log.txt` or `tests_skipped.md`.
9. `python -m haco postflight --run .haco/runs/latest --project .`
10. Report to the user only after completion.

See "HACO Usage Rule" below for a drop-in `AGENTS.md`/`CLAUDE.md` snippet.

## Output files

```
.haco/runs/latest/
  input.md                # the task
  project_snapshot.json   # scan + repo_map (size-budgeted)
  worker_outputs/*.json   # per-worker JSON (.error.json on failure)
  task_packet.json        # compact contract for the main agent
  execution_brief.md      # what the main agent reads first
  candidates/             # candidate packages (see below)
  prior_change_reference.md  # last commit that touched the edit target (code tasks; if any)
  metrics.json            # cost-tracking signals
  report.md               # postflight (after run)
  postflight_packet.json  # postflight effectiveness data
```

For `code_change` / `refactor` / `test_failure` tasks, HACO records the most recent
commit diff that touched `files_to_edit[0]` as `prior_change_reference.md` and points to
it from the brief — a concrete template for repetitive, incremental work (e.g. a marker
chain). It is git-based, deterministic, and provider-independent; absent for non-code
tasks or when there is no prior commit/edit target.

## candidates directory

Each candidate is a directory, not a bare diff:

```
candidates/candidate_01/
  candidate.json          # metadata + judge status
  edit_plan.md            # short plan for the main agent
  search_replace.json     # exact search/replace edits (no line numbers)
  replacement_blocks.md   # whole-function/class replacements
  optional.diff           # optional reference only
```

Candidates are **review material, not verified answers**.

### Hard filtering

`candidate_judge` plus rules split candidates into `accepted` (shown in the brief),
`masked` (kept on disk, only counted in the brief), and `rejected` (moved to
`candidates/rejected/`, never shown). This stops the main agent from wasting tokens
reviewing junk.

### Why not raw `.diff`

LLM-generated unified diffs break on line numbers, surrounding context, and
indentation drift. HACO treats `.diff` as optional reference and prefers
edit_plan / search_replace / replacement_blocks.

## Repository map

`scanner.py` extracts a structural skeleton (not full file contents): Python via the
built-in `ast` (classes, functions, signatures, imports, docstring previews), and
best-effort regex symbol hints for JS/TS/Rust/Go. tree-sitter is optional. repo_map
failure never fails preflight.

With `scanner.respect_gitignore: true` (default), files ignored by git (via
`git check-ignore`) are dropped from the scan, so generated/scratch outputs don't
pollute `files_to_read` or keyword matches. No filtering when git is unavailable.

## Token / size budget & structural trimming

HACO estimates tokens as `chars / 4` and enforces budgets on the snapshot, repo_map,
brief, task packet, and candidates. Trimming is **structural** — it drops list items,
shrinks symbol arrays, and shortens fields without ever cutting JSON or Markdown code
fences mid-structure. If trimming can't fit the budget, it falls back to a minimal
valid snapshot.

## Bounded exploration & mandatory validation

The brief does not say "don't explore" (that fights the agent's own system prompt).
Instead it requires a **mandatory first-step validation** recorded as a
`HACO Validation` section, and allows **bounded exploration** starting from
`files_to_read` and `search_keywords` when candidates are missing or wrong.

## HACO effectiveness tracking

`postflight` reads the `HACO Validation` section and records whether the main agent
actually used HACO, candidate usefulness, and whether broad exploration was needed —
so you can tell over time whether HACO is saving cost.

## skip_to_main_agent

If a core worker fails, the snapshot can't be built, or the file locator stays
low-confidence after a 2-pass focused rescan, HACO sets
`haco_status=skip_to_main_agent` with a `skip_reason` (e.g. `locator_failed`,
`provider_failure`, `repo_map_missing`) and tells the agent to proceed with normal
bounded exploration. This prevents garbage-in/garbage-out.

## Bootstrap (11-key Gemma review)

`python -m haco bootstrap` runs a temporary 11-reviewer design pass over the contract
(mock or google). It is scaffolding for building HACO itself: reviewers may critique
and propose but never edit files or log key values.

## Safety

- Never modifies target project files in default mode.
- Never logs API key values.
- Worker/provider failures degrade to per-worker fallbacks; preflight keeps going.

## Limitations

- repo_map is Python-first; JS/TS/Rust/Go are best-effort and may be wrong.
- `primary_language` / `test_frameworks` detection is best-effort.
- Whether HACO truly saves cost is judged from accumulated postflight data.
- The agent cannot be forced to follow the brief; HACO measures, it doesn't compel.
- For long task instructions, prefer `--task-file`.

## HACO Usage Rule (drop-in for a target project's AGENTS.md / CLAUDE.md)

```md
## HACO Usage Rule

When the user says "use haco", "하코 사용", or asks to reduce expensive model usage:

1. If the user task is long, multiline, or likely to exceed shell argument limits, write it to `.haco/task_input.md` or another temporary task file first.
2. Run one of:
   - `python -m haco preflight --project . --task "<user task>"`
   - `python -m haco preflight --project . --task-file .haco/task_input.md`
3. Read `.haco/runs/latest/task_packet.json`.
4. Read `.haco/runs/latest/execution_brief.md`.
5. Inspect accepted candidates in `.haco/runs/latest/candidates/`.
6. Prefer adapting HACO candidates before writing a patch from scratch.
7. Do not blindly apply `optional.diff`; prefer edit_plan/search_replace/replacement_blocks.
8. Apply changes yourself.
9. Run the recommended tests unless clearly impossible.
10. Write execution results into the HACO run directory:
   - execution_result.md
   - diff_summary.md
   - test_log.txt or tests_skipped.md
11. In execution_result.md, include a `HACO Validation` section.
12. Run `python -m haco postflight --run .haco/runs/latest --project .`.
13. Report to the user only after completion.

Do not ask the user for minor decisions if HACO says `user_decision_needed=false`.
If HACO says `haco_status=skip_to_main_agent`, proceed with normal bounded exploration.
```

## References

- Aider: repository map, search/replace style edit format
- SWE-agent: agent-computer interface and bounded tool use
- AlphaCodium: code generation as multi-stage flow engineering
