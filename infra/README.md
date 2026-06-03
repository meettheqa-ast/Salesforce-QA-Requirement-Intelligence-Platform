# infra/

Local development and deployment infrastructure.

## Current contents

- `docker/docker-compose.yml` — Postgres (pgvector), Redis, MinIO for local dev.

## Planned

- `docker/Dockerfile.api` — production image for `apps/api`
- `docker/Dockerfile.web` — production image for `apps/web`
- `terraform/` — AWS infrastructure (deferred until hosting target is confirmed)
- `migrations/` — operational migration runbooks
