# Runbook

Operational reference. Updated as functionality lands.

## Prerequisites

- Docker Desktop (or compatible)
- Python 3.12+
- `uv` — `pip install uv` or via the Astral installer
- Node 20+
- `pnpm` — `npm install -g pnpm`

## First-time setup

```bash
# from repo root
cp .env.example .env       # populated in Batch 2
docker compose -f infra/docker/docker-compose.yml up -d
```

## Running the API (apps/api)

Verified working as of Sprint 0 Batch 2.

```powershell
# One-time: install uv (https://docs.astral.sh/uv/) if not present
# Add uv to PATH for the session (Windows):
$env:Path = "$HOME\.local\bin;$env:Path"

# Start Postgres (host port 5433 to avoid clashing with native Postgres on 5432)
docker compose -f infra/docker/docker-compose.yml up -d postgres

# From apps/api:
uv sync                       # install deps into .venv (Python 3.12, pinned)
uv run alembic upgrade head   # apply migrations (connects as superuser sfqa)
uv run uvicorn app.main:app --reload --port 8000

# Health check
curl http://localhost:8000/healthz      # {"status":"ok"}

# Mint a dev token (AUTH_PROVIDER=dev only) and call /me
# POST /api/v1/auth/dev-token { "user_id": "...", "tenant_id": "...", "role": "tenant_admin" }
```

### Database roles (important)

- `sfqa` — superuser, used ONLY for migrations. Bypasses RLS.
- `sfqa_app` — restricted (NOSUPERUSER, NOBYPASSRLS), used by the app at runtime.
  Created automatically by `infra/docker/initdb/01-app-role.sql` on first
  container start. RLS only protects you when the app uses this role.

If you change RLS policies, recreate the volume to re-run init:
`docker compose -f infra/docker/docker-compose.yml down -v && ... up -d`.

## Quality gates (run before pushing)

```powershell
# from apps/api
uv run ruff check .          # lint
uv run mypy app              # strict typecheck
uv run lint-imports          # module boundary enforcement
uv run pytest -q             # tests (RLS isolation test requires Postgres up)
```

## Running the web app (apps/web)

Populated in **Sprint 0 Batch 3.** Not yet runnable.

## Common operations

Populated as features land.

## Troubleshooting

Populated as we encounter and document real problems.
