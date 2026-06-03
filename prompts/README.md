# prompts/ — Prompts as code

Every LLM prompt used by the platform lives here, versioned, loaded at runtime by the `ai_client` module.

## Convention

Filename: `<capability>/<task>.v<N>.md`. Examples:

- `analysis/triage.v1.md` — cheap-model first-pass triage of a single requirement
- `analysis/deep.v1.md` — Opus-class deep analysis after triage flags risk
- `qa/answer.v1.md` — RAG Q&A answering prompt
- `test_generation/planner.v1.md` — scenario outline planner
- `test_generation/executor.v1.md` — per-scenario test case body generator
- `salesforce_knowledge/entity_extraction.v1.md` — pulls SF entities from requirement text
- `salesforce_knowledge/cloud_classifier.v1.md` — cheap classifier verifying rule-based cloud detection

## Front matter

Each prompt file starts with a YAML front matter block:

```yaml
---
prompt_id: analysis.triage
version: 1
model_class: cheap          # cheap | primary
expected_output: json       # json | text
schema_ref: schemas/analysis_triage.v1.json
description: First-pass triage of a single Jira story to flag stories worth deep analysis.
---
```

The loader (`ai_client._internal.prompt_loader`) parses this and binds the prompt to a stable `(prompt_id, version)` key. Every LLM call records `(prompt_id, version)` on the resulting artifact.

## Rules

- **Never edit a published prompt in place.** Create `<task>.v<N+1>.md`.
- **Every prompt produces structured output** validated by a Pydantic schema (`apps/api/app/modules/ai_client/_internal/schemas/`).
- **Citations are mandatory** in any prompt that reads requirement or SF-knowledge content. The validation schema enforces this — unsourced claims fail validation.
- **Prompt-injection hygiene:** content retrieved from Jira or SF docs is wrapped in clearly delimited blocks (`<retrieved_content>...</retrieved_content>`) and the system prompt instructs the model to never follow instructions from those blocks.

Stub prompts land in Sprint 0 Batch 2. First real prompts land in Sprint 1 once the `analysis` module is being built.
