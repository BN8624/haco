# HACO Canon

HACO means **Harness for Agent Cost Optimization**.

HACO is a cost-reduction and work-efficiency harness for AI coding workflows.

HACO uses deterministic tools, free or low-cost workers, structured context extraction, candidate generation, verification loops, and run records to reduce the work done by expensive main coding agents.

HACO is not the final coding agent.

HACO does not directly modify target project files.

HACO prepares context, packets, candidates, summaries, logs, and reports.
The main coding agent reads those outputs, applies changes, runs or verifies tests, and reports to the user.

---

## §1. One-Line Definition

HACO is a preflight and postflight harness that reduces expensive main-agent reading, searching, repeated testing, log reading, and mechanical summarization by using cheaper workers and deterministic tools first.

Short form:

```text
Use cheap deterministic tools first.
Use free or low-cost workers second.
Use expensive main-agent reasoning last.
```

---

## §2. Primary Purpose

The primary purpose of HACO is **cost reduction**.

The user’s intent is:

```text
Use free or low-cost workers more,
so expensive paid coding agents do less unnecessary work.
```

HACO should reduce:

1. full-file reading,
2. broad repository searching,
3. repeated test execution,
4. long log reading,
5. mechanical diff summaries,
6. mechanical status reports,
7. repeated pattern matching,
8. duplicate reasoning across sessions,
9. unnecessary context loading,
10. unnecessary main-agent exploration.

HACO succeeds only if the main coding agent reads less, searches less, repeats less, and reaches decisions faster.

---

## §3. Non-Goals

HACO is not:

1. a replacement for the main coding agent,
2. an autonomous code modifier,
3. a tool that blindly applies patches,
4. a dashboard-first project,
5. an MCP-server-first project,
6. a multi-agent debate system,
7. a documentation sprawl system,
8. a full repository packer,
9. a system that asks the user to read long documents,
10. a system that creates more review burden than it removes.

More workers are not automatically better.

More documents are not automatically better.

More context is not automatically better.

HACO must reduce useful work for the expensive main agent, not create extra work.

---

## §4. User Role

The user is a vibe coder.

The user is not expected to read long project documents.

The user should:

1. define direction,
2. approve or reject major decisions,
3. receive short reports,
4. copy/paste prepared instructions when needed,
5. avoid manual code or document maintenance where possible.

The user should not be asked to inspect long Markdown files unless there is no practical alternative.

The user should not be asked repeated process questions when the agent can safely decide and record the reason.

User-facing reports should be short and decision-oriented.

Preferred report format:

```text
Changed:
Tests:
Commit:
Push:
Remaining risk:
Next:
```

---

## §5. Main Coding Agent Role

The main coding agent may be Claude Code, Codex, GPT, or another coding agent.

The main coding agent is still responsible for:

1. reading HACO outputs,
2. judging candidate quality,
3. applying or adapting edits,
4. running or verifying tests,
5. making final implementation decisions,
6. writing execution results,
7. committing only approved files,
8. reporting honestly to the user.

The main coding agent must not blindly trust HACO.

HACO candidates are advisory.

If HACO output is weak, the main coding agent should say so and continue with bounded exploration.

---

## §6. HACO Role

HACO performs work before and after the main coding agent.

HACO should produce:

1. project snapshot,
2. repo map,
3. task packet,
4. execution brief,
5. focused context pack,
6. candidate edits,
7. test candidate summaries,
8. document/report drafts,
9. run metrics,
10. postflight report,
11. failure-fix candidates when logs are available.

HACO should not:

1. directly edit target project files,
2. auto-apply patches,
3. auto-commit,
4. auto-push,
5. hide uncertainty,
6. preserve bad candidates as if they were useful,
7. force full-canon or full-repo reading.

---

## §7. Core Pipeline

HACO has three main phases.

```text
preflight → main agent work → postflight
```

### 7.1 Preflight

Preflight happens before broad file reading or editing.

It should:

1. scan the project,
2. detect language and project type,
3. detect test framework,
4. build repo map,
5. extract relevant files, symbols, sections, and keyword windows,
6. route the task,
7. compress the task,
8. locate likely files,
9. create focused context,
10. generate candidate edits or test candidates when useful,
11. filter candidates,
12. write task packet and execution brief.

Primary outputs:

```text
.haco/runs/latest/task_packet.json
.haco/runs/latest/execution_brief.md
.haco/runs/latest/context_pack.md
.haco/runs/latest/context_pack.json
.haco/runs/latest/candidates/
.haco/runs/latest/metrics.json
```

### 7.2 Main Agent Work

The main coding agent reads HACO outputs first.

Required reading order for a HACO run:

1. `context_pack.md` if present,
2. `task_packet.json`,
3. `execution_brief.md`,
4. accepted candidates.

The main agent then applies or adapts changes manually.

The main agent records:

```text
.haco/runs/latest/execution_result.md
.haco/runs/latest/diff_summary.md
.haco/runs/latest/test_log.txt
```

or:

```text
.haco/runs/latest/tests_skipped.md
```

### 7.3 Postflight

Postflight happens after the main agent finishes work.

It should:

1. read execution result,
2. read diff summary,
3. read test log or skipped-test note,
4. extract verifier/test status,
5. generate postflight report,
6. generate postflight packet,
7. evaluate HACO usefulness,
8. create failure-fix candidate only when failure logs exist.

Primary outputs:

```text
.haco/runs/latest/report.md
.haco/runs/latest/postflight_packet.json
.haco/runs/latest/auto_diff_summary.md
```

---

## §8. Cost Reduction Strategy

HACO reduces cost by moving work away from expensive main-agent reasoning.

Priority order:

1. deterministic Python tools,
2. existing project scripts,
3. free or low-cost LLM workers,
4. expensive main coding agent.

Highest-value offload targets:

1. file and symbol discovery,
2. focused context extraction,
3. markdown section extraction,
4. keyword windows,
5. git diff summarization,
6. test log compression,
7. verifier status extraction,
8. repeated pattern detection,
9. candidate edit drafting,
10. failure log analysis.

Do not use LLM workers for work that deterministic code can do more reliably.

Examples:

```text
Good deterministic work:
- parse Python AST
- extract markdown heading section
- collect git status
- summarize changed file list
- detect failed pytest node
- extract verifier PASS/FAIL

Good low-cost worker work:
- summarize selected excerpt
- draft candidate edit
- propose test case
- explain likely failure cause
- draft commit message

Bad low-cost worker work:
- final correctness judgment
- blind patch application
- broad unconstrained design debate
```

---

## §9. Context Offloading

Context offloading is one of HACO’s highest-value purposes.

Bad HACO output:

```text
Read phase0_engine.py.
```

Good HACO output:

```text
Read phase0_engine.py lines 420-510.
Relevant symbol: write_summary()
Reason: this function serializes validation summary fields.
```

HACO should provide focused context instead of forcing the main agent to read whole files.

Focused context types:

1. symbol excerpt,
2. class excerpt,
3. function excerpt,
4. markdown heading section,
5. keyword window,
6. nearby prior-change diff,
7. compressed test output,
8. compressed verifier output.

Primary output:

```text
context_pack.md
context_pack.json
```

The context pack must be budgeted.

It must not become a full repository dump.

If HACO cannot build a useful context pack, it should clearly say why.

---

## §10. Symbol and Section Tools

HACO should internalize the useful idea from tools like Serena and RTK without depending on them by default.

Do not add external Serena, RTK, or MCP dependencies by default.

Instead, implement core ideas internally.

Useful internal functions:

```text
get_project_overview()
build_repo_map()
find_symbol()
read_symbol()
find_references()
read_markdown_section()
extract_keyword_windows()
compress_command_output()
compress_test_log()
compress_git_diff()
```

Python source files should use AST when possible.

Markdown files should use heading sections.

Unknown text files should use keyword windows.

Large files should be excerpted, not copied whole.

---

## §11. Repo Map

The repo map is a compact representation of the project.

It should include:

1. file paths,
2. primary language,
3. important symbols,
4. class/function names,
5. signatures when available,
6. line ranges,
7. imports when useful,
8. short docstring or comment preview.

It should not include full file contents.

Example:

```json
{
  "file": "src/example.py",
  "symbols": [
    {
      "kind": "function",
      "name": "run_task",
      "signature": "run_task(task: str) -> dict",
      "line_start": 42,
      "line_end": 88,
      "docstring_preview": "Runs one task..."
    }
  ]
}
```

The repo map should help HACO select file ranges and symbols before the main agent reads files.

---

## §12. File Locator

The file locator should not only return files.

It should return focused ranges when possible.

Preferred output:

```json
{
  "files_to_read": [
    {
      "file": "phase0_engine.py",
      "line_start": 420,
      "line_end": 510,
      "reason": "write_summary serializes validation summary fields",
      "confidence": "high"
    }
  ],
  "files_to_edit": [
    {
      "file": "CURRENT_STATUS.md",
      "reason": "status document must reflect validation result",
      "confidence": "high"
    }
  ]
}
```

If locator confidence is low, HACO should perform a focused second pass.

If the second pass still fails, set:

```text
haco_status=skip_to_main_agent
```

and record the reason.

---

## §13. Candidate Package

HACO should not rely on raw unified diff as the primary candidate format.

Candidate outputs should be directories.

Preferred candidate directory:

```text
candidate_01/
  candidate.json
  edit_plan.md
  search_replace.json
  replacement_blocks.md
  optional.diff
```

Priority order:

1. full function/class replacement block,
2. search/replace block,
3. anchor-based insertion,
4. edit plan,
5. optional unified diff.

`optional.diff` is advisory only.

The main agent must not blindly apply it.

Candidate metadata should include:

1. target files,
2. confidence,
3. risk,
4. assumptions,
5. apply method,
6. judge status,
7. why accepted/masked/rejected.

---

## §14. Candidate Filtering

HACO must avoid showing weak candidates as useful.

Candidate judge statuses:

```text
accepted
masked
rejected
```

Only accepted candidates should appear prominently in `execution_brief.md`.

Weak candidates should be masked or rejected.

Under the Fail Closed rule, weak or speculative candidates must not be shown as useful.

Reject or mask candidates when:

1. target files are missing,
2. target symbols or sections are missing,
3. apply method is unclear,
4. search/replace is placeholder,
5. search/replace anchor matches zero or multiple locations,
6. confidence is low and risk is high,
7. deterministic evidence is missing,
8. candidate does not match the task,
9. candidate requires broad guessing,
10. candidate is only a vague strategy without useful anchors.

If all candidates are weak, HACO should say so.

This is better than forcing the main agent to review garbage.

---

## §15. Provider Policy

HACO should support at least:

```text
mock
google
```

### 15.1 Mock Provider

Mock provider is deterministic and free.

It is useful for:

1. testing HACO itself,
2. validating pipeline structure,
3. exercising candidate directories,
4. testing postflight,
5. avoiding API cost.

Mock provider is not expected to produce strong real code candidates.

### 15.2 Google Provider

Google provider is for Gemini/Gemma worker use.

It should support:

1. multiple API keys,
2. key rotation,
3. 429 backoff,
4. timeout handling,
5. JSON parsing fallback,
6. no API key logging.

Google provider should be used when actual low-cost worker output is needed.

### 15.3 Provider Safety

Never log raw API keys.

Never commit `.env`.

Never assume provider output is correct.

---

## §16. Multi-Agent Strategy

Multi-agent work is a means, not a goal.

Use multiple workers only when they reduce main-agent work.

Useful worker types:

1. task router,
2. context compressor,
3. file locator,
4. patch candidate generator,
5. test candidate generator,
6. document reporter,
7. candidate judge,
8. failure fixer.

Avoid:

1. large debate loops,
2. repeated opinions,
3. excessive voting,
4. multi-agent work that produces more text for the main agent to read.

The best worker output is short, structured, and directly useful.

---

## §17. Harness Engineering

HACO must control unreliable worker output.

Required harness features:

1. strict schemas,
2. JSON validation,
3. fallback behavior,
4. skip reasons,
5. candidate filtering,
6. budget trimming,
7. deterministic run directories,
8. metrics,
9. test coverage,
10. no silent failure.

If a core worker fails, HACO should not pretend success.

If HACO cannot help, it should say so and fall back safely.

---

## §17.1 Fail Closed and Confidence Calibration

HACO must fail closed.

HACO must not produce rich context, accepted candidates, or long speculative reports when confidence is low.

Low-confidence output should become shorter, not longer.

LLM self-reported confidence is not enough.

High confidence requires deterministic evidence such as:

1. exact file/path evidence,
2. exact symbol or markdown section evidence,
3. traceback or test/log evidence,
4. stable search anchors,
5. agreement between independent deterministic signals,
6. small and focused context ranges.

If confidence is low, HACO must:

1. avoid speculative candidates,
2. avoid long context packs,
3. write a short skip reason,
4. set `haco_status=skip_to_main_agent`,
5. let the main agent continue with bounded exploration.

Weak candidates must be masked or rejected, not shown as useful.

The most dangerous HACO failure is not failing to help.

The most dangerous HACO failure is giving the main agent polluted context with high confidence.

Recommended confidence pipeline:

```text
Hard Gate → Evidence Score → Budget Gate → Output Mode
```

Hard Gate examples:

```text
fail_closed_if:
- task intent cannot be classified
- relevant file candidates exceed the configured limit
- top candidate and second candidate are too close
- files are found but no symbol, section, or line range can be narrowed
- only LLM evidence exists and no deterministic evidence exists
- candidate references a missing file, symbol, or section
- search/replace anchor matches zero or multiple locations
- candidate confidence is high but verifiable evidence is missing
- context_pack exceeds the configured budget
```

Recommended initial thresholds:

```text
HIGH_THRESHOLD = 70
MEDIUM_THRESHOLD = 45

MAX_FILES_HIGH = 3
MAX_FILES_MEDIUM = 5

MAX_RANGE_LINES_HIGH = 200
MAX_RANGE_LINES_MEDIUM = 500

MAX_CONTEXT_PACK_TOKENS = 8000
MAX_EXECUTION_BRIEF_LINES = 150

MIN_SCORE_GAP_HIGH = 15
MIN_DETERMINISTIC_SIGNALS_HIGH = 2
```

These thresholds are not correctness guarantees.

They are pollution-prevention gates.

LLM confidence may support a decision, but it must not be the primary evidence.

---

## §18. Loop Engineering

HACO is not only preflight.

The full loop is:

```text
preflight
→ main agent work
→ postflight
→ failure analysis
→ next candidate
→ next run
```

Each run should record what happened.

Postflight should answer:

1. Did HACO help?
2. Were candidates useful?
3. Did the main agent need broad exploration?
4. Were tests run?
5. Did failures occur?
6. What should improve next?

This allows future runs to become cheaper and better.

---

## §19. Test and Log Compression

HACO should reduce log-reading cost.

It should eventually support:

1. pytest output compression,
2. verifier output compression,
3. git diff summary,
4. git status summary,
5. command output filtering,
6. failure category extraction.

Raw logs may still be stored, but the main agent should first see compressed summaries.

Example compressed test summary:

```text
Status: failed
Failed test: tests/test_example.py::test_parse
Key error: AssertionError expected PASS got UNKNOWN
Likely files: haco/postflight.py, tests/test_postflight.py
Full log: test_log.txt
```

---

## §20. Document System

All projects using this style should follow the shared Markdown rules.

Default document set:

```text
AGENTS.md
CLAUDE.md
<PROJECT>_CANON.md
DOCS_INDEX.md
HANDOFF.md
CHECKLIST.md
```

`AGENTS.md` and `CLAUDE.md` should be byte-identical unless explicitly stated otherwise.

The canon is the source of truth.

The index routes the AI to the relevant canon sections.

Handoff tells the next session where things stand.

Checklist prevents repeated mistakes.

The user is not expected to read long documents.

Document roles:

```text
AGENTS.md / CLAUDE.md = short operating rules
<PROJECT>_CANON.md = stable source of truth
DOCS_INDEX.md = compact reading router
HANDOFF.md = current state
CHECKLIST.md = active task checks
```

Do not duplicate long canon content into `AGENTS.md`, `CLAUDE.md`, or `DOCS_INDEX.md`.

If the index becomes so long that reading it costs more than it saves, shrink it.

---

## §21. Canon and Index Reading Rule

The canon may be long.

The main agent must not read the whole canon by default.

The main agent should:

1. read `AGENTS.md` or `CLAUDE.md`,
2. read `HANDOFF.md`,
3. read `CHECKLIST.md`,
4. read `DOCS_INDEX.md`,
5. select the smallest matching route,
6. read only the specified canon sections,
7. report which route and sections were selected before editing.

If no route matches, read only:

1. `§1 One-Line Definition`,
2. the one section whose title best matches the task.

If the task is a review of the document system itself, combine the document-system route and the review route instead of reading the full canon.

Do not read full canon unless explicitly requested or the index is clearly broken.

---

## §22. Repository Boundary

If multiple repositories are involved, keep them separate.

Example:

```text
haco = tool repository
godseed = target project repository
```

Rules:

1. do not create target project code inside HACO,
2. do not create HACO source inside target projects,
3. check `pwd`, `git remote -v`, and `git status` before editing,
4. commit each repository separately,
5. report each repository separately.

Do not use `git add -A`.

Stage explicit files only.

Do not commit `.haco/`.

---

## §23. Default HACO Usage Rule

For non-trivial repository work, HACO should be the default.

HACO should run before broad file reading or editing.

Examples where HACO should run:

1. code changes,
2. multi-file edits,
3. document restructuring,
4. repo review,
5. debugging,
6. test failure analysis,
7. validation result reporting,
8. refactoring,
9. anything likely to require multiple file reads.

HACO may be skipped without asking the user when:

1. the task is clearly trivial,
2. no repository file reading or editing is needed,
3. the task is only reviewing uploaded standalone files,
4. HACO is unavailable and the reason is reported,
5. running HACO would obviously cost more time/context than it saves.

When HACO is skipped, record the skip reason.

Ask the user only when skipping HACO creates material risk or changes the requested workflow.

Skipping HACO silently on non-trivial repository work is a process violation.

---

## §24. Metrics and Effectiveness

HACO must measure whether it helped.

Important metrics:

1. haco_status,
2. skip_reason,
3. fail_closed_triggered,
4. fail_closed_reason,
5. confidence_tier,
6. evidence_score,
7. deterministic_signal_count,
8. files_to_read count,
9. focused ranges count,
10. context_pack size,
11. candidates generated,
12. candidates accepted/masked/rejected,
13. candidate usefulness,
14. bounded exploration needed,
15. tests run/skipped,
16. postflight status.

Effectiveness categories:

```text
usable
partially_usable
unusable
none
```

HACO should optimize for actual usefulness, not just running workers.

Minimum cost-reduction metrics should include:

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
bounded_exploration_needed:
tests_run:
tests_skipped_reason:
fail_closed_triggered:
fail_closed_reason:
confidence_tier:
evidence_score:
deterministic_signal_count:
```

Recommended default budgets:

```text
context_pack.md: prefer under 8k estimated tokens
execution_brief.md: prefer under 150 lines
candidate list shown to main agent: accepted candidates only, unless debugging candidate quality
```

If these budgets are exceeded, HACO should explain why.

HACO should not claim success merely because it ran.

HACO succeeds only when it reduces main-agent reading, searching, repetition, verification burden, or handoff cost.

---

## §25. Success Criteria

HACO succeeds if:

1. main agent reads less,
2. main agent searches less,
3. repeated testing/log reading is reduced,
4. context packs are useful,
5. candidates are actionable or honestly marked weak,
6. low-confidence tasks fail closed,
7. postflight records what happened,
8. new sessions resume faster,
9. costs decrease,
10. project purpose does not drift.

HACO fails if:

1. it produces long noisy outputs,
2. it forces review of bad candidates,
3. it causes more reading than it saves,
4. it hides weak confidence,
5. it creates documentation sprawl,
6. it becomes a dashboard or debate system before solving context offload,
7. it asks the user to read long files,
8. it repeatedly asks the user process questions the agent can safely decide,
9. it gives polluted context to the main agent with high confidence.

---

## §26. Implementation Priority

Highest priority:

1. context offloading,
2. symbol and section extraction,
3. focused context packs,
4. deterministic output compression,
5. candidate quality and filtering,
6. fail-closed confidence calibration,
7. postflight effectiveness.

Lower priority:

1. dashboard,
2. MCP server,
3. complex UI,
4. large multi-agent debates,
5. direct auto-patching,
6. packaging polish before dogfooding.

Do not optimize for architectural beauty before cost reduction is proven.

---

## §27. Current Strategic Direction

The next strategic direction is:

```text
Move HACO from “file locator” to “context offloader.”
```

That means HACO should not only say:

```text
Read this file.
```

It should say:

```text
Read this symbol, section, or line range.
Here is the excerpt.
Here is why it matters.
Here is what was omitted.
```

This is the strongest path toward reducing expensive main-agent token use.

---

## §28. Final Rule

HACO exists to make expensive coding agents do less unnecessary work.

If a feature does not reduce main-agent reading, searching, repetition, verification burden, handoff cost, or confidence calibration, it is not a priority.

HACO is not a tool that helps as much as possible.

HACO is a tool that helps only when it can help safely.
