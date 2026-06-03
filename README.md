# TestingBuddy — Salesforce QA Requirement Intelligence Platform

A Salesforce-aware requirement intelligence layer that sits *before* test design: ingests Jira requirements, builds persistent project knowledge repositories, detects gaps and ambiguities, answers questions with citations, and generates test artifacts grounded in Salesforce domain knowledge.

## Status

**Sprint 0 — Foundation in progress.** Not yet runnable end-to-end.

## Source-of-truth documents

Read these in order before contributing:

1. `PRD + Agent Architecture Specification.txt` — original product spec
2. `.cursor/plans/sf_qa_rip_architecture_*.plan.md` — target-state architecture
3. `.cursor/plans/sf_qa_rip_execution_plan_*.plan.md` — execution plan (scope freeze, sprint roadmap, risk register, simplification calls)
4. `DECISIONS.md` — every meaningful technical decision
5. `docs/AGENTS.md` — rules for AI coding agents working on this repo
6. `docs/RUNBOOK.md` — how to run things locally

## High-level shape

- **`apps/api`** — FastAPI service (Python 3.12, `uv`). Modular monolith with 18 module packages.
- **`apps/web`** — Next.js 15 App Router (TypeScript, `pnpm`). Tailwind + shadcn/ui + `react-zero-skeleton`.
- **`packages/shared-types`** — OpenAPI-generated TypeScript types consumed by the web app.
- **`prompts/`** — Prompts-as-code. Versioned. Every artifact stamped with the prompt version that produced it.
- **`infra/docker`** — `docker-compose.yml` for local Postgres + Redis + (later) MinIO.

## How to run (placeholder — populated in Batch 3 of Sprint 0)

```bash
# Prereqs: Docker, uv (https://docs.astral.sh/uv/), pnpm, Node 20+, Python 3.12+

# 1. Start infrastructure
docker compose -f infra/docker/docker-compose.yml up -d

# 2. Bootstrap API
cd apps/api
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

# 3. Bootstrap web (separate terminal)
cd apps/web
pnpm install
pnpm dev
```

## Working without API keys

The platform boots with stub providers for every external service. Set `AI_PROVIDER=stub` and `JIRA_PROVIDER=stub` in `.env` to run end-to-end without Anthropic, OpenAI, or a Jira instance. Stub responses are deterministic.

To plug in real services, copy `.env.example` to `.env` and fill in credentials. No code change required.

## Contributing

- Module boundaries are enforced by `import-linter`. Import only from `<module>.api`.
- Every PR runs lint, typecheck, tests, import-linter, and a synthetic cross-tenant RLS probe.
- See `docs/AGENTS.md` for AI-agent-specific rules.

## License

Proprietary. Not yet licensed for redistribution.
