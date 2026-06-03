# apps/api — FastAPI backend

Modular monolith. Populated in **Sprint 0 Batch 2.**

## Module layout (planned)

Each is a Python package under `app/modules/<name>/` with a strict `api/` public surface and `_internal/` private implementation.

- `auth` — OIDC validation, tenant context propagation
- `tenants` — Tenant + User + Membership CRUD
- `connections` — Jira credential storage with envelope encryption
- `jira` — Jira HTTP client, normalization, sync workflows
- `repositories` — Repository + Version + Document lifecycle
- `rag` — Chunking, embedding, hybrid retrieval (pgvector + tsvector)
- `salesforce_knowledge` — Tier 1 docs + Tier 2 reasoning patterns + cloud classifier
- `analysis` — AnalysisRun + Finding
- `test_generation` — TestGenerationRun + TestCase
- `qa` — QASession + QAMessage
- `exports` — CSV/JSON exports to S3
- `publishing` — Publish to Jira (and later Xray/Zephyr) behind PublishAdapter
- `change_intelligence` — Diff between RepositoryVersions (V1; stub at MVP)
- `traceability` — Trace edges; coverage queries (V1)
- `ai_client` — Single chokepoint for LLM calls
- `jobs` — arq-based background jobs
- `audit` — Append-only audit events
- `metering` — Per-tenant usage rollups and budget checks
