# Architectural Decisions Log

This file records every meaningful technical decision for the Salesforce QA Requirement Intelligence Platform. New decisions are appended; old decisions are amended in-place with a strikethrough + replacement, never deleted.

Format per decision: `Date · Decision · Reasoning · Confidence · Reversible?`.

---

## D-0001 · 2026-06-03 · Monorepo over polyrepo

**Decision:** Single git repository organized as a monorepo.

**Layout:**

```
.
├── apps/
│   ├── api/                # FastAPI (Python 3.12, uv)
│   └── web/                # Next.js 15 App Router (TypeScript, pnpm)
├── packages/
│   └── shared-types/       # OpenAPI -> TypeScript codegen consumed by web
├── infra/
│   └── docker/             # docker-compose, Dockerfiles
├── prompts/                # Prompts-as-code, versioned, loaded at runtime
│   ├── analysis/
│   ├── qa/
│   ├── test_generation/
│   └── salesforce_knowledge/
├── docs/                   # Runbooks, architecture, agent rules
└── .github/workflows/      # CI
```

**Reasoning:** atomic cross-stack changes (e.g., API contract change + UI consumer) land in one PR; single CI history; small team multiplies productivity from one toolchain. Microservice extraction later is by directory move, not by repo split.

**Confidence:** [Likely]. **Reversible:** Yes — split into two repos is a `git filter-repo` exercise if scale demands it.

---

## D-0002 · 2026-06-03 · uv for Python, pnpm for Node

**Decision:** `uv` (Astral) for Python dependency + venv management. `pnpm` for Node workspace management.

**Reasoning:**
- `uv` is faster than pip/poetry by 10–100x and has emerged as the modern Python default. [Likely]
- `pnpm` handles workspaces (apps/web + packages/shared-types) better than npm/yarn and is faster than both. [Certain]

**Confidence:** [Likely]. **Reversible:** Yes — both produce standard lockfiles; switching tools is config-only.

---

## D-0003 · 2026-06-03 · Stubs-first for external dependencies

**Decision:** Every external integration (Anthropic, OpenAI, Jira, OIDC provider) has a `Stub*Provider` implementation selected via env var. Real providers plug in by setting credentials; no code change.

**Reasoning:**
- Foundation must boot and pass tests without external API keys (offline CI, new-developer onboarding, deterministic tests).
- Silent fakes that pretend to call real services are worse than honest stubs that say "I'm a stub." This decision codifies the second behavior.
- Stub responses are *canned* (deterministic JSON fixtures), not random — every behavior testable.

**Confidence:** [Certain]. **Reversible:** N/A — abstraction stays; only the default flips.

---

## D-0004 · 2026-06-03 · Anthropic primary, OpenAI for embeddings, Bedrock failover deferred to V1

**Decision:** Anthropic API (direct) for LLM calls; OpenAI `text-embedding-3-small` for embeddings; no Bedrock at MVP.

**Reasoning:** Single vendor per concern reduces ops surface during MVP. Bedrock failover is a V1 problem worth solving after we have actual production traffic to measure. Voyage embeddings deferred until we have retrieval-quality data justifying the second vendor.

**Confidence:** [Likely]. **Reversible:** Yes — `ai_client` is provider-abstracted from day one.

---

## D-0005 · 2026-06-03 · Modular monolith with strict import discipline

**Decision:** Single deployable FastAPI service (`apps/api`) composed of 18 module packages. Cross-module access via `<module>.api` namespace only; enforced by `import-linter` in CI.

**Reasoning:** Documented in detail in `docs/ARCHITECTURE.md` and `docs/EXECUTION_PLAN.md`. Microservices on day one would tax a small team. Module boundaries are the logical service boundaries; extraction later is a refactor, not a rewrite.

**Confidence:** [Certain]. **Reversible:** Yes; extraction path documented.

---

## D-0006 · 2026-06-03 · Postgres + pgvector + Redis + S3 (or S3-compatible) for MVP

**Decision:** Postgres 16 with pgvector extension for primary storage including embeddings; Redis for cache + rate-limit + job queue; S3 (or local MinIO in dev) for export artifacts.

**Reasoning:** One database is simpler than two. pgvector is good to ~2M vectors with proper indexing; the architecture plan defines the Qdrant migration trigger. Redis is unavoidable for jobs + rate limits.

**Confidence:** [Likely]. **Reversible:** Yes — vector access goes through `rag` module; swap is contained.

---

## D-0007 · 2026-06-03 · arq for background jobs (not Celery, not Temporal yet)

**Decision:** `arq` (Redis-backed async job runner) for MVP background work.

**Reasoning:** Temporal is the right answer for the *target* state. arq is the right answer for MVP: Redis already in stack, async-native, ~200 lines of configuration vs Temporal's operational surface. The `jobs` module wraps arq behind an interface — Temporal swap is contained.

**Confidence:** [Likely]. **Reversible:** Yes.

---

## D-0008 · 2026-06-03 · Next.js 15 App Router + Tailwind + shadcn/ui + skelter

**Decision:** UI is Next.js 15 with App Router, Tailwind, shadcn/ui (Radix-based components, copy-paste), `react-zero-skeleton` (a.k.a. `skelter`) for loading states, TanStack Query for server-state.

**Rejected UI references (from the 5 GitHub repos evaluated 2026-06-03):**
- `liquidglass` — WebGL shader-based glass effects. Rejected for a B2B QA tool: bundle weight, GPU cost, accessibility risk, decorative rather than functional. May appear once on auth/marketing surface; not in-app.
- `ui-ux-pro-max-skill` — Useful one-time to pick a design system; not a runtime dependency.

**Adopted UI references:**
- `react-zero-skeleton` (skelter) — runtime dependency for loading skeletons across long-running analysis/Q&A.
- `LibreUIUX-Claude-Code` workflow — adopted as *discipline*, not as plugins: speak Tailwind tokens (not vague aesthetics); use `/ui-critique` style review loop; screenshot-iterate against the live UI.
- `ui-ux-pro-mcp` — optional MCP server installed in the developer environment for design-resource lookup. Not a runtime dependency.

**Reasoning:** shadcn/ui is the default modern stack for data-dense B2B SaaS. skelter solves a real problem (skeleton-real-component drift) that bites every team. The other three references are noise for an enterprise QA product.

**Confidence:** [Likely]. **Reversible:** Yes for skelter (replace with manual skeletons); harder for shadcn/Tailwind once components proliferate.

---

## D-0009 · 2026-06-03 · OIDC-based auth with DevAuthProvider for local dev

**Decision:** Production uses an OIDC IdP (Auth0 or Cognito; specific provider deferred to V1). Local development uses a `DevAuthProvider` that issues fake JWTs signed with a dev-only secret.

**Reasoning:** Avoids the "every dev needs an IdP account" friction in Sprint 0–1. The auth interface is identical; only the provider flips.

**Confidence:** [Certain]. **Reversible:** N/A.

---

## D-0010 · 2026-06-03 · Postgres RLS for tenant isolation, mandatory and enforced

**Decision:** Every tenant-scoped table has a Postgres Row-Level Security policy keyed on `tenant_id`. The API layer sets `SET LOCAL app.current_tenant_id` per request. Tests include synthetic cross-tenant probes.

**Reasoning:** Application-layer tenant filtering is necessary but not sufficient. One forgotten `WHERE tenant_id = ?` becomes a cross-tenant data leak. RLS is the belt-and-suspenders backstop.

**Confidence:** [Certain]. **Reversible:** No — would need a security-engineering reason to remove.

---

## D-0011 · 2026-06-03 · Separate migration vs runtime DB roles (RLS correctness)

**Decision:** The application connects as a restricted role `sfqa_app`
(NOSUPERUSER, NOBYPASSRLS). Migrations connect as the superuser `sfqa` via a
separate `MIGRATION_DATABASE_URL`.

**Reasoning:** Discovered during Sprint 0 Batch 2 validation: Postgres
superusers and roles with BYPASSRLS *ignore* RLS policies entirely, even under
`FORCE ROW LEVEL SECURITY`. The default `POSTGRES_USER` in the pgvector image is
a superuser. An RLS isolation test correctly caught tenant A reading tenant B's
rows. The only correct fix is to run application queries as a non-superuser,
non-BYPASSRLS role. The role is created by `infra/docker/initdb/01-app-role.sql`
locally and by an explicit step in CI.

**Confidence:** [Certain] — verified by a passing cross-tenant isolation test.
**Reversible:** No — removing this reintroduces a cross-tenant data-leak class.

---

## D-0012 · 2026-06-03 · Postgres on host port 5433

**Decision:** The dev Postgres container maps to host port 5433, not 5432.

**Reasoning:** A natively-installed PostgreSQL was already listening on 5432 on
the development machine; asyncpg connected to it instead of the container,
causing auth failures. 5433 avoids the clash. Production is unaffected (uses its
own DNS/endpoint).

**Confidence:** [Certain]. **Reversible:** Yes — change the compose port mapping
and the two DB URLs.

---

## D-0013 · 2026-06-03 · RLS GUCs set via set_config(), not SET LOCAL

**Decision:** `tenant_session` sets the tenant GUC with
`SELECT set_config('app.current_tenant_id', :tid, true)` rather than
`SET LOCAL app.current_tenant_id = :tid`.

**Reasoning:** Postgres `SET` does not accept bind parameters; asyncpg's
prepared-statement protocol raised a syntax error on `SET LOCAL ... = $1`.
`set_config(name, value, is_local)` accepts parameters and is injection-safe.

**Confidence:** [Certain] — verified by tests. **Reversible:** N/A.

---

## Unresolved working assumptions (carry-over from execution plan)

These are *not* decisions yet. They are flagged risks awaiting user input:

1. **AI provider clarification** — current default: Anthropic direct (per D-0004). "Use Cursor API credentials" framing from earlier prompts was explicitly rejected.
2. **Hosting target** — assumed AWS; not yet committed.
3. **Pricing model** — assumed usage-based with monthly tier cap; metering is built, UI is V1.
4. **TestingBuddy event bus contract** — assumed Postgres outbox + Redis Streams; replace when TB defines its bus.
5. **Phase 3 SF org metadata** — explicitly Future, not MVP or V1.

Flag any of these for change in writing.
