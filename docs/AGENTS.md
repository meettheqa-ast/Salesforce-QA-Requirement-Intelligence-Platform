# AGENTS.md — Rules for AI coding agents working on this repository

This document is the contract any AI coding agent (Cursor, Claude Code, Copilot, others) must honor when editing this codebase. Humans should also read it, but it exists primarily because agents act fast and need rules they cannot drift from.

## Operating principles

1. **Source of truth ordering.** When two documents disagree, this is the precedence:
   1. `PRD + Agent Architecture Specification.txt` (product intent)
   2. `.cursor/plans/sf_qa_rip_architecture_*.plan.md` (target architecture)
   3. `.cursor/plans/sf_qa_rip_execution_plan_*.plan.md` (execution plan, MVP scope)
   4. `DECISIONS.md`
   5. Code as written
   If you find code that contradicts the higher documents, the code is wrong — surface it, do not silently match it.

2. **Truth over agreement.** This codebase is owned by a user who explicitly prefers honest pushback over validation. If a request conflicts with an architectural decision, say so before complying. If you're uncertain, mark `[Likely]` or `[Guessing]` rather than asserting facts.

3. **No emojis** in code, commit messages, comments, or generated documentation, unless the user explicitly asks.

## Hard rules

### Module boundaries

- Modules live under `apps/api/app/modules/<module_name>/`.
- Each module exposes its public surface from `<module>/api/__init__.py`. Nothing else is importable from outside the module.
- Cross-module access uses `from app.modules.<other_module>.api import X`. Never `from app.modules.<other>._internal...`.
- `import-linter` enforces this in CI. Do not work around it.

### Tenant isolation

- Every tenant-scoped query MUST run inside a request scope where `SET LOCAL app.current_tenant_id = '<uuid>'` has been set.
- Every tenant-scoped table has an RLS policy. Adding a new tenant-scoped table without an RLS policy will fail CI.
- Never select across tenants in application code, even for admin use cases. Cross-tenant operations go through a dedicated admin path with explicit audit emission.

### Secrets

- Real credentials live only in environment variables (loaded via `pydantic-settings`).
- Decrypted secrets exist only inside the `connections` module. They never appear in API responses, log lines, or test fixtures.
- The structured logger has a denylist for secret-shaped strings (Atlassian API tokens, OAuth bearer tokens, KMS DEKs).
- `.env` is in `.gitignore`. `.env.example` is the only env file committed.

### LLM calls

- All LLM calls go through `app.modules.ai_client.api.complete()`. No direct `anthropic.Anthropic()` calls anywhere else in the codebase.
- Every call passes `prompt_id` and `prompt_version`. Failure to pass them is a runtime error, not a warning.
- Every call records: model, prompt_version, input tokens, output tokens, cost_cents, tenant_id, request_id. These land in `audit_events` AND `usage_meter`.
- Budget check happens before the call. Exceeded budget raises `BudgetExceeded` and the LLM is never contacted.

### Prompts

- Prompts live in `prompts/<capability>/<task>.v<N>.md`.
- Adding a new prompt = bump version + add file + reference from code by `(prompt_id, version)`.
- Editing a published prompt in place is forbidden. Create a new version.

### Output validation

- Every LLM response that produces structured data is validated against a Pydantic schema.
- On validation failure: one repair retry with stricter instruction. Second failure logs the offending output and surfaces a typed error. Never silently accept invalid output.

### Database changes

- Schema changes go through Alembic migrations. No `Base.metadata.create_all()` in app code.
- Migrations are reviewed for: tenant_id presence, RLS policy, sensible indexes, and forward+backward compatibility.
- Destructive migrations (drop column, drop table) require an explicit two-step migration: write-compatible deprecation in migration N, removal in migration N+1.

### Tests

- Every module ships with: unit tests for its `api/` surface, integration tests touching the DB if it owns tables, and a synthetic cross-tenant probe if it owns tenant-scoped data.
- CI runs `ruff`, `mypy --strict`, `pytest`, `tsc --noEmit`, `biome check`, `import-linter`. All must pass.

## What you must NOT do

- Do not introduce a new external dependency without justification recorded in `DECISIONS.md`.
- Do not generate code that calls real Anthropic / OpenAI / Jira in tests. Use the stub providers.
- Do not edit `DECISIONS.md` to remove decisions; amend with strikethrough + replacement.
- Do not add emoji to any committed file unless the user explicitly asks.
- Do not create files outside the documented monorepo layout.
- Do not introduce LangGraph, Temporal, Qdrant, gRPC, or a vector DB other than pgvector during MVP. These are V1+ decisions and are deliberately deferred — see `.cursor/plans/sf_qa_rip_execution_plan_*.plan.md` Deliverable 9.
- Do not implement features classified as V1/V2/Future from Deliverable 1 of the execution plan unless the user explicitly upgrades the bucket.

## When you encounter ambiguity

- Prefer the simplest implementation consistent with the documented architecture.
- If a decision is needed that affects more than one module, stop and ask. Don't infer.
- If a decision is needed within one module, take the simpler path and record the decision in `DECISIONS.md`.

## When you complete a task

- Run lint + typecheck + tests locally before declaring done.
- Update `DECISIONS.md` if you made an architectural choice.
- Update the relevant section in `docs/RUNBOOK.md` if behavior changed.
- Don't claim a feature is "done" if its tests don't exist; mark it "implemented, tests pending."
