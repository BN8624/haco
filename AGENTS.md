# AGENTS.md

This project is HACO.

HACO means Harness for Agent Cost Optimization.

Goal:
Build and maintain a Python CLI that reduces expensive coding-agent usage by creating compact task packets and coding candidates before Codex/Claude Code performs real work.

Core rules:
- Keep the project CLI-first.
- HACO is used by coding agents, not primarily by the human user.
- Do not add MCP, web UI, dashboard, database, vector DB, or auto-editing unless explicitly requested.
- Mock mode must always work.
- Worker outputs must be JSON and schema-validated.
- HACO must not modify target project files in its default mode.
- Gemma workers are allowed to generate candidate packages, test candidates, and fix candidates.
- Do not rely on raw unified diff as the primary candidate format.
- Candidate directories must include candidate.json and, when possible, edit_plan.md/search_replace.json/replacement_blocks.md.
- candidate_judge must hard-filter low-quality candidates before they appear in execution_brief.md.
- Codex/Claude Code remains the final integrator and executor.
- Prefer small, deterministic, testable functions.
- Use Python AST repo_map as the required baseline; tree-sitter is optional.
- Apply token/size budgets so HACO does not become a context bloat source.
- Budget trimming must preserve JSON/Markdown structural integrity.
- Postflight must record HACO effectiveness signals.
- Bootstrap workers may review and propose, but must not edit files directly.
- Never log API key values.
- Keep reports short.
- Do not create unnecessary planning documents.
- Update README when CLI behavior changes.
- Do not ask the user about minor implementation choices.

The contract `HACO.md` is canonical. Do not edit it without the owner's approval.
