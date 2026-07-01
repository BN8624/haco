# HACO Agent Rules

This file is the mandatory operating guide for AI coding agents working on HACO.

`CLAUDE.md` and `AGENTS.md` must remain byte-identical. If one is changed, update the other with the exact same content.

After changing either file, verify:

```bash
cmp -s CLAUDE.md AGENTS.md && echo "identical" || echo "different"
```

Respond to the user in Korean unless the user explicitly requests another language.

---

## 1. Core Purpose

HACO means **Harness for Agent Cost Optimization**.

HACO exists to reduce expensive main-agent work by using cheap deterministic tools, free or low-cost workers, focused context extraction, candidate generation, and postflight records.

HACO is not an autonomous coding agent.

HACO does not directly modify target project files.

HACO prepares context, task packets, candidates, summaries, logs, and reports. The main coding agent applies changes, verifies tests, commits explicit files, and reports to the user.

Core rule:

```text
Use cheap deterministic tools first.
Use free or low-cost workers second.
Use expensive main-agent reasoning last.
```

Fail-closed rule:

```text
If confidence is low, HACO output must become shorter, not longer.
Do not give the main agent polluted context with high confidence.
```

---

## 2. Required Document Set

The project-control documents are:

1. `CLAUDE.md` / `AGENTS.md`
2. `HACO_CANON.md`
3. `DOCS_INDEX.md`
4. `HANDOFF.md`
5. `CHECKLIST.md`

Do not create additional long project-control documents unless the user explicitly approves.

Maintain a single root `README.md` whose sole audience is an AI coding agent using HACO from another project — how to invoke HACO, how to read its outputs, and a paste-in `HACO Usage Rule` block for the target project's `CLAUDE.md`/`AGENTS.md`. It is not a human-facing project overview; keep it usage-focused, not a philosophy essay. Do not create any other `README.md` elsewhere in the repository.

Document roles:

```text
CLAUDE.md / AGENTS.md = short operating rules
HACO_CANON.md = stable source of truth
DOCS_INDEX.md = compact reading router
HANDOFF.md = current state
CHECKLIST.md = active task safety
```

Do not duplicate long canon content into this file.

---

## 3. Default Reading Order

At the start of repository work, read only:

1. this file,
2. `HANDOFF.md`,
3. `CHECKLIST.md`,
4. `DOCS_INDEX.md`.

Then select the smallest matching route from `DOCS_INDEX.md`.

Before editing, report:

```text
Selected route:
Canon sections read:
Files expected to change:
HACO used/skipped:
```

For review-only work, report:

```text
Selected route:
Canon sections read:
Files expected to inspect:
HACO used/skipped:
```

Do not read full `HACO_CANON.md` unless:

1. the user explicitly asks for full canon review,
2. the task is to rewrite the canon itself,
3. `DOCS_INDEX.md` is clearly stale or broken,
4. multiple routes conflict and the conflict cannot be resolved.

If full canon is read, report why first.

---

## 4. HACO Default Workflow

HACO is the default workflow for non-trivial repository work.

Run HACO before broad file reading or editing for:

1. code changes,
2. multi-file edits,
3. document restructuring,
4. validation or result reporting,
5. debugging,
6. test failure analysis,
7. repo review,
8. refactoring,
9. anything likely to require multiple file reads.

HACO may be skipped without asking the user when:

1. the task is clearly trivial,
2. no repository file reading or editing is needed,
3. the task is only reviewing uploaded standalone files,
4. HACO is unavailable and the reason is reported,
5. running HACO would obviously cost more time/context than it saves.

Do not ask the user for HACO skip approval unless skipping creates material risk or changes the requested workflow.

When HACO is skipped, report the reason.

Skipping HACO silently on non-trivial repository work is a process violation.

---

## 5. Fail Closed and Confidence Calibration

HACO must fail closed.

Low-confidence HACO output should become shorter, not longer.

LLM self-reported confidence is not enough.

High confidence requires deterministic evidence such as:

1. exact file/path evidence,
2. exact symbol or markdown section evidence,
3. traceback or test/log evidence,
4. stable search anchors,
5. agreement between independent deterministic signals,
6. small and focused context ranges.

If confidence is low:

1. do not generate speculative candidates,
2. do not create a long context pack,
3. write a short skip reason,
4. set `haco_status=skip_to_main_agent`,
5. let the main agent continue with bounded exploration.

Weak candidates must be masked or rejected, not shown as useful.

The most dangerous HACO failure is not failing to help.

The most dangerous HACO failure is giving the main agent polluted context with high confidence.

---

## 6. Required HACO Flow

1. Confirm repository identity:

```bash
pwd
git remote -v
git status
```

2. If the task is long or multiline, write it to:

```text
.haco/task_input.md
```

3. Run preflight:

```bash
python -m haco preflight --project . --task-file .haco/task_input.md
```

or for short tasks:

```bash
python -m haco preflight --project . --task "<task>"
```

4. Before editing, read:

```text
.haco/runs/latest/context_pack.md
.haco/runs/latest/task_packet.json
.haco/runs/latest/execution_brief.md
.haco/runs/latest/candidates/
```

Read `context_pack.md` first if present.

5. If `haco_status=skip_to_main_agent`, continue with bounded exploration and record the skip reason.

6. HACO candidates are advisory. Do not apply blindly.

7. After work, write:

```text
.haco/runs/latest/execution_result.md
.haco/runs/latest/diff_summary.md
.haco/runs/latest/test_log.txt
```

or:

```text
.haco/runs/latest/tests_skipped.md
```

8. `execution_result.md` must include:

```text
## HACO Validation

haco_used: yes/no
haco_skip_reason: none/trivial/no_repo_file_work/uploaded_file_review/unavailable/not_cost_effective/other
haco_skip_approved_by_user: yes/no/not_applicable
haco_status: completed/skip_to_main_agent/failed
fail_closed_triggered: yes/no
fail_closed_reason:
confidence_tier: high/medium/low/none
evidence_score:
deterministic_signal_count:
task_packet_read: yes/no
execution_brief_read: yes/no
context_pack_read: yes/no/not_present
accepted_candidates_checked: yes/no
candidate_usefulness: usable | partially_usable | unusable | none
bounded_exploration_needed: yes/no
reason:
```

9. When possible, include cost-reduction metrics:

```text
estimated_main_agent_files_avoided:
estimated_lines_avoided:
context_pack_lines:
context_pack_tokens_estimate:
execution_brief_lines:
extra_files_read_after_haco:
accepted_candidates_count:
masked_candidates_count:
rejected_candidates_count:
candidate_used:
tests_run:
tests_skipped_reason:
```

10. Run postflight:

```bash
python -m haco postflight --run .haco/runs/latest --project .
```

11. Do not commit `.haco/`.

---

## 7. Repository Boundary Rule

Multiple repositories may be active.

Do not mix them.

If working on HACO:

1. work only inside the HACO repository,
2. HACO may dogfood itself,
3. run HACO tests such as `pytest` and `python -m haco doctor`,
4. do not create external project code inside HACO.

If working on another project such as GODSEED:

1. work only inside that project repository,
2. use HACO as a tool,
3. do not modify HACO source files from the external project task,
4. do not copy HACO source into the external project.

When two repositories need changes, make separate commits and separate reports.

Always check repository identity before editing.

---

## 8. Commit and File Safety

Never use:

```bash
git add -A
```

Stage only explicit files.

Before committing:

1. run `git status`,
2. confirm no `.haco/`, scratch, cache, or stray copied files are staged,
3. run relevant tests or explain why skipped,
4. keep the commit scoped to one repository and one purpose.

Do not push unless the user explicitly approves in the current task or has approved push for this exact commit.

---

## 9. Document Maintenance Rules

Do not let documents sprawl.

`CLAUDE.md` and `AGENTS.md` are rules, not design essays.

`HACO_CANON.md` is canon, not handoff.

`DOCS_INDEX.md` is routing, not duplicated content.

`HANDOFF.md` is current state, not history.

`CHECKLIST.md` is active checks, not general documentation.

When a discussion becomes long:

1. extract the stable decision into `HACO_CANON.md`,
2. update `DOCS_INDEX.md` only if routing changes,
3. put only current state in `HANDOFF.md`,
4. put active checks in `CHECKLIST.md`,
5. do not preserve long debate unless the user asks.

If editing `CLAUDE.md` or `AGENTS.md`:

1. update both files with exact same content,
2. verify byte identity with `cmp -s CLAUDE.md AGENTS.md`,
3. report the verification result.

---

## 10. Implementation Priority

Prefer changes that reduce expensive main-agent work.

Highest priority:

1. context offloading,
2. symbol and section extraction,
3. focused context packs,
4. deterministic output compression,
5. candidate quality and filtering,
6. fail-closed confidence calibration,
7. postflight effectiveness.

Lower priority unless explicitly requested:

1. dashboard,
2. MCP server,
3. complex UI,
4. large multi-agent debate,
5. direct auto-patching,
6. packaging polish before dogfooding.

Main strategic direction:

```text
Move HACO from “file locator” to “context offloader.”
```

If a feature does not reduce main-agent reading, searching, repetition, verification burden, handoff cost, or confidence calibration, it is not a priority.

---

## 11. Reporting Format

Use concise Korean reports.

For completed work, report:

```text
Changed:
Tests:
Commit:
Push:
Remaining risk:
Next:
```

For multi-repository work, report separately:

```text
HACO:
- Changed:
- Tests:
- Commit/Push:

TARGET PROJECT:
- Changed:
- Tests:
- Commit/Push:
```

Be honest about failed tests, skipped tests, uncommitted files, untracked files, uncertainty, and incomplete work.
