# @sfqa/web

Next.js 15 (App Router) frontend for the Salesforce QA Requirement Intelligence
Platform.

## Stack

- **Next.js 15** App Router, **React 18.3** (see DECISIONS D-0015), TypeScript
- **Tailwind CSS** + shadcn-style primitives (`src/components/ui`)
- **TanStack Query** for server state
- **react-zero-skeleton** (skelter) for loading states, confined to
  `src/components/skeleton.tsx` (see DECISIONS D-0016)
- Types shared from `@sfqa/shared-types` (OpenAPI-generated; see D-0017)

## Run (from repo root)

```bash
pnpm install
pnpm dev:web        # http://localhost:3000
```

The app expects the API at `NEXT_PUBLIC_API_BASE_URL` (default
`http://localhost:8000`). Copy `.env.example` to `.env.local` to override.

## Dev login

There is no real IdP in Sprint 0. The home page (`/`) mints a local bearer token
via the API's `POST /auth/dev-token` (only enabled when `AUTH_PROVIDER=dev`),
stores it in `localStorage`, and redirects to `/dashboard`, which verifies the
session against `GET /auth/me`. Sprint 1 replaces this with OIDC.

## Quality gates

```bash
pnpm --filter @sfqa/web typecheck
pnpm --filter @sfqa/web lint
pnpm --filter @sfqa/web build
```

## Regenerate shared types

```bash
pnpm gen:types      # FastAPI -> openapi.json -> packages/shared-types/src/openapi.ts
```
