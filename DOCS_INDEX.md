# DOCS_INDEX

This file is the compact reading router for `HACO_CANON.md`.

Do not read `HACO_CANON.md` top-to-bottom by default.

For each task:

1. read this router,
2. select the smallest matching route,
3. read only the listed canon sections,
4. report the selected route and sections before editing.

If following this index causes more reading than it saves, shrink this index.

---

## Required Report Before Editing

```text
Selected route:
Canon sections read:
Files expected to change:
HACO used/skipped:
```

For review-only tasks, use:

```text
Selected route:
Canon sections read:
Files expected to inspect:
HACO used/skipped:
```

---

## Route Table

| Route                                                     | Use When                                                                                                                               | Read                                                     |
| --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| 0. Canon / Index / Agent Rules Review                     | reviewing consistency of `HACO_CANON.md`, `DOCS_INDEX.md`, `CLAUDE.md`, `AGENTS.md`, reading rules, document burden                    | §1, §2, §3, §4, §17, §17.1, §20, §21, §23, §24, §25, §28 |
| 1. Document System / Markdown Rules                       | modifying project-control docs, shared Markdown rules, reading order, context budget rules                                             | §1, §2, §4, §20, §21, §23                                |
| 2. HACO Purpose / Strategy / Scope Review                 | reviewing purpose, non-goals, user role, main-agent role, project direction, feature fit                                               | §1, §2, §3, §4, §5, §6, §25, §28                         |
| 3. Preflight Pipeline                                     | modifying preflight, task packets, execution briefs, task routing, context compressor, file locator, preflight metrics                 | §1, §6, §7, §8, §12, §17, §17.1, §24                     |
| 4. Context Offloading / Symbol Tools                      | modifying `context_pack`, symbol tools, markdown section extraction, keyword windows, focused line ranges                              | §1, §2, §8, §9, §10, §11, §12, §17.1, §27, §28           |
| 5. Repo Map / Scanner / File Discovery                    | modifying scanner, repo map, project snapshot, language/test detection, file filtering, keyword extraction                             | §1, §8, §9, §11, §12, §17, §17.1                         |
| 6. Candidate Package / Patch Candidate / Test Candidate   | modifying candidate dirs, candidate schema, edit plans, replacement blocks, test candidates, candidate judge                           | §1, §6, §7, §13, §14, §17, §17.1, §24                    |
| 7. Provider / Google / Gemma / API Keys                   | modifying provider abstraction, Google/Gemini/Gemma calls, keys, rotation, 429 backoff, timeouts, JSON fallback                        | §1, §8, §15, §16, §17, §24                               |
| 8. Multi-Agent / Worker Harness / Concurrency             | modifying worker orchestration, worker schemas, async/concurrency, worker outputs, candidate judge sequencing                          | §1, §6, §7, §16, §17, §17.1, §18, §24                    |
| 9. Postflight / Effectiveness / Failure Fixer             | modifying postflight, execution result parsing, test log parsing, reports, effectiveness metrics, failure fixer                        | §1, §7, §17.1, §18, §19, §24, §25                        |
| 10. Test and Log Compression / RTK-Style Output Filtering | modifying output filtering, pytest summaries, verifier summaries, diff summaries, command output reducers                              | §1, §8, §10, §18, §19, §24, §27                          |
| 11. Repository Boundary / Git Safety / Multi-Repo Work    | modifying repo boundary rules, `.haco/` commit prevention, staging rules, push rules, multi-repo reporting                             | §1, §4, §5, §22, §23                                     |
| 12. Default HACO Usage Rule / Agent Behavior              | modifying HACO default workflow, skip rules, fail-closed behavior, process violations, main-agent obligations, validation requirements | §1, §2, §5, §6, §17.1, §21, §23, §24                     |
| 13. Library / CLI / Packaging                             | modifying CLI commands, package layout, public API, pyproject, install behavior, entrypoints                                           | §1, §6, §7, §17, §22, §25                                |
| 14. Review / Audit / “꼼꼼히 봐줘”                             | repo review, critical review, audit, “냉정하게 평가”, “문제점 찾아”, “완성인지 봐”                                                                     | §1, §2, §3, §8, §9, §17, §17.1, §24, §25, §26, §28       |
| 15. Handoff / Session Restart                             | preparing handoff, updating `HANDOFF.md`, compressing current status, avoiding context bloat                                           | §1, §4, §20, §21, §22                                    |
| 16. New Feature Prioritization                            | deciding whether a proposed feature should be built now, later, or rejected                                                            | §1, §2, §3, §8, §17.1, §25, §26, §27, §28                |
| 17. Fail Closed / Confidence Calibration                  | modifying confidence tiers, evidence scoring, hard gates, skip reasons, low-confidence output behavior                                 | §1, §3, §8, §14, §17, §17.1, §24, §25, §28               |

---

## Route Selection Rules

When multiple routes match:

1. choose the smallest route that covers the task,
2. add one extra canon section only if necessary,
3. report the added section and why it was needed,
4. do not read the full canon by default.

If the task is implementation plus document update:

1. select the implementation route first,
2. add `§20 Document System` only if project-control docs are changed,
3. do not switch to a full document route unless the main task is document restructuring.

If the task is reviewing the document system itself:

1. use Route 0,
2. add Route 14 only if broader project effectiveness is also being judged,
3. do not read unrelated provider, candidate, or implementation sections.

If the task involves confidence calibration or low-confidence behavior:

1. use Route 17,
2. add the implementation route only if code changes are required,
3. do not read the full canon.

If the task involves another repository:

1. apply that repository’s own document rules first,
2. use HACO canon only for HACO-specific behavior,
3. keep commits and reports separated.

---

## If No Route Matches

Do not read the full canon.

Read only:

```text
HACO_CANON.md §1 One-Line Definition
HACO_CANON.md — the one section whose title best matches the task
```

Then report:

```text
Selected route: no exact route
Canon sections read:
Reason:
```

Continue with bounded exploration.

---

## Full Canon Reading Policy

Full `HACO_CANON.md` reading is allowed only when:

1. the user explicitly asks for full canon review,
2. the task is to rewrite the canon itself,
3. this index is clearly stale or broken,
4. multiple routes conflict and the conflict cannot be resolved.

If full canon is read, report why first:

```text
Full canon read: yes
Reason:
```

---

## General Exclusions

Unless directly relevant, do not read:

1. provider sections for document-only tasks,
2. candidate package sections for routing-only tasks,
3. document system sections for pure implementation tasks,
4. archive/history files,
5. full source files when symbol or section ranges are enough.

---

## Final Rule

`DOCS_INDEX.md` is a router, not a table of contents.

Its job is to prevent unnecessary canon reading.
