# apps/web — Next.js 15 App Router frontend

Populated in **Sprint 0 Batch 3.**

## Stack

- Next.js 15 (App Router, React Server Components)
- TypeScript (strict)
- Tailwind CSS
- shadcn/ui (Radix-based)
- `react-zero-skeleton` (a.k.a. skelter) — auto-generated skeleton loaders
- TanStack Query — server-state caching
- API types consumed from `packages/shared-types` (OpenAPI codegen)

## Pages planned for MVP (per execution plan Deliverable 1)

- `/` — Repository list (tenant-scoped)
- `/repositories/new` — Create from JQL or issue-key list
- `/repositories/[id]` — Overview
- `/repositories/[id]/analysis` — Findings with citations
- `/repositories/[id]/qa` — Chat with citations
- `/repositories/[id]/test-cases` — Generated cases, approval, export
- `/connections` — Jira connections
- `/jobs` — Long-running job status
- `/settings` — Members, budget, audit log
