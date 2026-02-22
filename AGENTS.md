# DedupTickets — Agent Guidelines

Ticket deduplication & clustering platform. FastAPI + Azure Cosmos DB backend, React frontend.
See [.rules/ARCHITECTURE.md](.rules/ARCHITECTURE.md) for system design, layers, and data model.

## Critical Rules

1. **No file-system writes** — serverless is read-only. Process everything in-memory. → [.rules/SERVERLESS.md](.rules/SERVERLESS.md)
2. **Async everything** — use `aiohttp`, `asyncio.gather()`, and `async def` handlers. → [.rules/ASYNC_PATTERNS.md](.rules/ASYNC_PATTERNS.md)
3. **Pin exact versions + sync both files every change** — any dependency update in `requirements.txt` or `pyproject.toml` must update the other file in the same change, with exact `==` pins. → [.rules/DEPENDENCIES.md](.rules/DEPENDENCIES.md)
4. **Standardized responses** — every endpoint returns `request_id` + `performance` metrics. → [.rules/API_STANDARDS.md](.rules/API_STANDARDS.md)
5. **Pass all quality gates** — lint, format, security, typecheck, tests (80% coverage). → [.rules/QUALITY_GATES.md](.rules/QUALITY_GATES.md)
6. **Reuse before writing** — check for existing helpers and patterns first. → [.rules/PATTERNS.md](.rules/PATTERNS.md)
7. **Run the checklist** — verify every applicable item before marking work done. → [.rules/CHECKLIST.md](.rules/CHECKLIST.md)
8. **Text-only human input** — never use checkbox/radio UI; ask questions as plain text with numbered options. → [.rules/AGENT_INTERACTION.md](.rules/AGENT_INTERACTION.md)
9. **Date-stamped feature branches** — name branches `feature/<topic>-<YYYY-MM-DD>`, always merge to main before branching. → [.rules/BRANCHING.md](.rules/BRANCHING.md)
10. **Frontend theme compliance** — use `primary-*` tokens, component classes, and `dark:` variants on every element; never hardcode `blue-*`/`indigo-*`. → [.rules/FRONTEND_THEME.md](.rules/FRONTEND_THEME.md)
11. **Frontend quality gates** — every frontend change must pass lint, format, typecheck, build, and tests before completion. → [.rules/QUALITY_GATES.md](.rules/QUALITY_GATES.md)

## Navigation

| Topic | File | When to Read |
|-------|------|-------------|
| System architecture | [.rules/ARCHITECTURE.md](.rules/ARCHITECTURE.md) | Understanding the codebase, adding domains |
| Serverless constraints | [.rules/SERVERLESS.md](.rules/SERVERLESS.md) | Any file I/O or deployment work |
| Async patterns | [.rules/ASYNC_PATTERNS.md](.rules/ASYNC_PATTERNS.md) | HTTP calls, parallel operations |
| Quality gates | [.rules/QUALITY_GATES.md](.rules/QUALITY_GATES.md) | After any code change (backend or frontend) |
| Frontend theme & styling | [.rules/FRONTEND_THEME.md](.rules/FRONTEND_THEME.md) | Adding or modifying frontend components |
| API response format | [.rules/API_STANDARDS.md](.rules/API_STANDARDS.md) | Adding or modifying endpoints |
| Dependency management | [.rules/DEPENDENCIES.md](.rules/DEPENDENCIES.md) | Adding or updating packages |
| Code patterns & helpers | [.rules/PATTERNS.md](.rules/PATTERNS.md) | Implementing features, removing features |
| Pre-completion checklist | [.rules/CHECKLIST.md](.rules/CHECKLIST.md) | Before marking any task done |
| Quality scoring | [.rules/QUALITY_SCORE.md](.rules/QUALITY_SCORE.md) | Reviewing gaps, planning improvements |
| Execution plans | [.rules/exec-plans/README.md](.rules/exec-plans/README.md) | Complex multi-step work |
| Runtime & observability | [.rules/RUNTIME.md](.rules/RUNTIME.md) | Function structure, timeouts, retry, logging |
| Functions runtime v4 runbook | [.rules/RUNTIME.md](.rules/RUNTIME.md) | Running/debugging local Azure Functions host |
| Agent interaction | [.rules/AGENT_INTERACTION.md](.rules/AGENT_INTERACTION.md) | Asking clarifying questions, capturing user input |
| Cosmos DB best practices | [.github/skills/cosmosdb-best-practices/SKILL.md](.github/skills/cosmosdb-best-practices/SKILL.md) | Any Cosmos DB work |
| Cosmos DB field naming | [.rules/COSMOS_FIELD_NAMING.md](.rules/COSMOS_FIELD_NAMING.md) | Indexing policies, excluded paths, queries |
| Env sync (.env ↔ local.settings.json) | [.rules/RUNTIME.md](.rules/RUNTIME.md) | Updating connection values for either entry point |
| Branching strategy | [.rules/BRANCHING.md](.rules/BRANCHING.md) | Creating feature branches, merging to main |

## Reading Order for New Tasks

1. This file (you're here) — get the map
2. [.rules/ARCHITECTURE.md](.rules/ARCHITECTURE.md) — understand the system
3. The topic doc relevant to your task (see Navigation above)
4. [.rules/CHECKLIST.md](.rules/CHECKLIST.md) — verify completeness before finishing

## Runtime & Observability

Thin handlers, explicit timeouts, retry with backoff, singleton clients, structured logging. → [.rules/RUNTIME.md](.rules/RUNTIME.md)

## Self-Governance Rules

1. **AGENTS.md is the map, not the encyclopedia.** Keep it under 120 lines. Add detail to a topic doc in `.rules/` and only add a one-liner pointer here. New rules require a topic doc in `.rules/`; never add multi-line detail inline.
2. **Enforce mechanically when possible.** Run `make lint-docs` to validate structure. When a rule can be checked by a linter, promote it from documentation into code (see custom lint error messages in [.rules/QUALITY_GATES.md](.rules/QUALITY_GATES.md)).
3. **Keep docs fresh.** If you change behavior covered by a topic doc, update the doc in the same PR. Stale docs are worse than no docs.
4. **Track quality.** After addressing a gap, update the grade in [.rules/QUALITY_SCORE.md](.rules/QUALITY_SCORE.md).
5. **Use execution plans for complex work.** Create a plan in [.rules/exec-plans/active/](.rules/exec-plans/active/) before starting multi-step tasks. Move to `completed/` when done.
