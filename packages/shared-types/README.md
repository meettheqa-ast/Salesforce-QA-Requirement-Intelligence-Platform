# packages/shared-types

Generated TypeScript types derived from the FastAPI OpenAPI schema. Consumed by `apps/web` for end-to-end type safety across the HTTP boundary.

Generation pipeline (wired in Sprint 0 Batch 3):

1. `apps/api` exposes OpenAPI at `/openapi.json`.
2. `pnpm gen:types` runs `openapi-typescript` against a running API (or a committed snapshot).
3. Output lands in `src/api.ts` and is imported by `apps/web` as `@sfqa/shared-types`.

This package contains no hand-written types. Edit the API; regenerate.
