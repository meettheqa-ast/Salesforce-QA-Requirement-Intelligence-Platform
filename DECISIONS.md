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

## D-0014 · 2026-06-03 · pnpm via npm-global + corepack disabled

**Decision:** pnpm 11.5.1 is installed via `npm install -g pnpm` (user-writable
prefix), not corepack. Approved native builds are pinned in `pnpm-workspace.yaml`
under `onlyBuiltDependencies` (sharp, unrs-resolver).

**Reasoning:** corepack failed with EPERM writing to `C:\Program Files\nodejs`
(admin-only) on this machine. The npm-global prefix is user-writable. pnpm 11
moved `onlyBuiltDependencies` out of package.json into the workspace file.

**Confidence:** [Certain]. **Reversible:** Yes — switch to corepack with elevated
permissions if desired.

---

## D-0015 · 2026-06-03 · React 18.3, not the React 19 RC

**Decision:** apps/web pins React 18.3.1 even though Next 15.0.3 also accepts the
React 19 RC.

**Reasoning:** For a foundation we intend to maintain, an RC on the critical path
trades stability for nothing we need yet. 18.3 has stable `@types/react@18` and
fewer ecosystem mismatches. Upgrade to 19 is a deliberate, separate step.

**Confidence:** [Likely best for stability]. **Reversible:** Yes — bump React +
types and re-test.

---

## D-0016 · 2026-06-03 · skelter confined behind a local wrapper

**Decision:** `react-zero-skeleton` (skelter) is the chosen runtime skeleton lib
(per the UI/UX decision), but every import is confined to
`apps/web/src/components/skeleton.tsx`.

**Reasoning:** skelter 1.0.2 was published the day before adoption — single
maintainer, 25 churned versions, and a packaging quirk (`types` points to a
`.d.ts` not shipped; only `.d.mts` is present). Wrapping it makes a future swap a
one-file change and contains supply-chain/stability risk on the load-state path.

**Confidence:** [Likely] this risk is real. **Reversible:** Yes — replace the
wrapper internals.

---

## D-0017 · 2026-06-03 · OpenAPI-driven shared types with a hand-maintained fallback

**Decision:** `packages/shared-types` generates `src/openapi.ts` from the API's
OpenAPI schema (`pnpm gen:types`); the generated file is gitignored. A small set
of hand-maintained shapes in `src/index.ts` is the committed fallback.

**Reasoning:** Committing generated code invites drift and noisy diffs. But CI and
fresh clones must compile without running the Python exporter, so a minimal
typed fallback keeps the web build self-sufficient. Codegen is the source of
truth when present.

**Confidence:** [Certain]. **Reversible:** Yes — commit the generated file instead
if a single source is preferred.

---

## D-0018 · 2026-06-03 · OIDC = Auth0-primary, claims-first with DB fallback

**Decision:** Real OIDC verification (RS256 + JWKS cache + issuer/audience/exp
checks) targets Auth0 as the primary IdP but stays configurable. `tenant_id`/
`role` resolve claims-first (namespaced custom claims), falling back to a DB
membership lookup by token subject/email when claims are absent. A token claim
that disagrees with the DB membership is rejected (403).

**Reasoning:** Auth0 needs namespaced custom claims, which not every token will
carry; a DB fallback keeps auth working without forcing claim configuration,
while the disagreement check prevents a user asserting a tenant they don't
belong to — the tenant-isolation boundary must not be bypassable via a forged
claim.

**Confidence:** [Certain] for the verification path (unit-tested with a local
RSA key + mocked JWKS: valid/expired/wrong-aud/wrong-iss/tampered/no-claims).
**Reversible:** Yes — claim names and fallback are configurable.

---

## D-0019 · 2026-06-03 · Auth dependency is async; providers only verify

**Decision:** Auth providers (`verify`) do crypto + claim extraction only and
return `VerifiedClaims`. The FastAPI dependency `get_current_principal` is async
and owns Principal resolution (including the DB fallback).

**Reasoning:** DB lookup is async and needs a session; keeping it out of the
provider keeps providers pure and testable without a DB, and puts the
security-critical tenant decision in one place.

**Confidence:** [Certain]. **Reversible:** Low cost.

---

## D-0020 · 2026-06-03 · First user-facing LLM path = POST /api/v1/qa/ask

**Decision:** A minimal authenticated `qa.ask` endpoint runs the versioned
`qa.answer` prompt through the `ai_client.complete()` chokepoint. No retrieval
yet (Sprint 4); the prompt is told context is empty. Budget exceedance returns
HTTP 402; provider failure returns 502.

**Reasoning:** Budget enforcement could only be proven via tests before this; a
real endpoint makes the budget gate observable end-to-end and gives Sprint 1 a
tangible vertical slice without pulling Sprint 4 retrieval forward.

**Confidence:** [Certain] — endpoint tested (stub answer, auth-required, 402
over-budget). **Reversible:** Yes.

---

## D-0021 · 2026-06-03 · LLM calls go to Anthropic directly; NOT through Cursor

**Decision:** Reaffirmed: the product's runtime LLM traffic calls Anthropic
directly. Cursor credentials are never used for product inference. The live
Anthropic acceptance call is deferred until a real `sk-ant-` key is available;
Sprint 1 ships stub-verified.

**Reasoning:** Cursor's API/SDK is for agentic dev tooling, not a sanctioned
production inference backend. Routing product traffic through it risks
terms-of-use violation, loses per-tenant cost attribution (which the metering/
budget design depends on), cedes model control, and adds a data processor. A
`crsr_` token was offered as an inference key; it was declined and the user
confirmed the real motive was simply lacking an Anthropic key. If vendor
flexibility becomes a goal, the path is a provider-agnostic gateway behind the
existing `ai_client` abstraction — not Cursor.

**Confidence:** [Certain]. **Reversible:** N/A (a no-op reaffirmation of D-0004).

---

## D-0022 · 2026-06-03 · Default models bumped to current SDK ids

**Decision:** `anthropic_model_primary` = `claude-opus-4-8`,
`anthropic_model_cheap` = `claude-haiku-4-5` (from the older opus-4-5 default),
matching ids the installed anthropic SDK (0.105.2) advertises.

**Confidence:** [Likely] these are current. **Reversible:** Yes — env override
plus the two settings defaults.

---

## D-0023 · 2026-06-04 · Envelope encryption lives in app/crypto.py (infra, not a module)

**Decision:** Secret sealing/opening is an app-level utility (`app/crypto.py`),
not a domain module, so it is exempt from module-boundary import rules — like
`db.py`. Only `connections` may call it (enforced by convention + AGENTS.md).
Scheme: random per-secret AES-256-GCM DEK, DEK wrapped by a KEK from the KMS;
local KEK derives a 32-byte key from `KMS_LOCAL_MASTER_KEY` via SHA-256.
AWS/GCP KEKs raise NotImplemented rather than silently weakening.

**Reasoning:** A `kms` domain module would add boundary ceremony for pure
infrastructure. Keeping it app-level mirrors the existing `db`/`crypto` split.

**Confidence:** [Certain] for the local path (round-trip + tamper tests).
**Reversible:** Yes — promote to a module if it grows domain logic.

---

## D-0024 · 2026-06-04 · connections is the only secret-decrypting module

**Decision:** `connections.get_credentials_for_use(connection_id, purpose)` is
the single decrypt path; it audits every use (action + purpose, never the secret)
and is the only function that returns plaintext credentials — to in-process
callers only. No schema serializes a decrypted secret to an HTTP response;
`ConnectionOut` omits it entirely.

**Reasoning:** Concentrating decryption in one audited chokepoint mirrors the
ai_client LLM chokepoint and makes credential exposure reviewable in one place.

**Confidence:** [Certain] — tested: persisted row never contains plaintext;
in-process retrieval returns the real secret. **Reversible:** Low value to.

---

## D-0025 · 2026-06-04 · Tenant-scoped rows set tenant_id explicitly from context

**Decision:** `create_*` functions on tenant-scoped tables set
`tenant_id = require_tenant_id()` on the ORM object. `tenant_session` sets the
RLS GUC for filtering but does NOT populate the column.

**Reasoning:** RLS `WITH CHECK` rejects an INSERT whose `tenant_id` is NULL —
caught by tests as an `InsufficientPrivilegeError` before shipping. The GUC
governs visibility; the column must still be written. (Bug found and fixed in
Batch A.)

**Confidence:** [Certain]. **Reversible:** Could add an ORM default that reads
the context var, but explicit is clearer for an audited boundary.

---

## D-0026 · 2026-06-04 · Chunks table now, chunking logic in Sprint 3

**Decision:** `repository_document_chunks` is created in the Sprint 2 migration
for schema stability, but no code populates it and the embedding vector column
is deferred to the Sprint 3 (RAG) migration (so we don't pin a dimension before
choosing the embeddings provider).

**Confidence:** [Certain]. **Reversible:** Yes.

---

## D-0027 · 2026-06-04 · Version ingestion is idempotent on (repository, key)

**Decision:** `ingest_version` is a no-op-returning-existing when a version with
the same `sync_idempotency_key` already exists for the repository. Versions are
immutable, monotonically numbered snapshots.

**Reasoning:** Sync jobs can be retried (arq); idempotency prevents duplicate
versions from a re-run. **Confidence:** [Certain] — tested. **Reversible:** Yes.

---

## Unresolved working assumptions (carry-over from execution plan)

These are *not* decisions yet. They are flagged risks awaiting user input:

1. **AI provider clarification** — RESOLVED. Anthropic direct (D-0004, reaffirmed D-0021). Cursor-credential routing explicitly declined again on 2026-06-03. Live key still pending for the one-time live acceptance call.
2. **Hosting target** — assumed AWS; not yet committed.
3. **Pricing model** — assumed usage-based with monthly tier cap; metering is built, UI is V1.
4. **TestingBuddy event bus contract** — assumed Postgres outbox + Redis Streams; replace when TB defines its bus.
5. **Phase 3 SF org metadata** — explicitly Future, not MVP or V1.

Flag any of these for change in writing.
