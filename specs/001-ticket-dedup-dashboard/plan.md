# Implementation Plan: Ticket Deduplication & Clustering Dashboard

**Branch**: `001-ticket-dedup-dashboard` | **Date**: 2026-01-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-ticket-dedup-dashboard/spec.md`

## Summary

Build a ticket deduplication and clustering dashboard that enables support teams to reduce duplicate handling effort through automated cluster suggestions with human-controlled merge operations. The system will use Python/FastAPI for the backend API, Azure Cosmos DB for NoSQL for persistence with async operations, and a React frontend. Clustering will use field matching (transaction ID, error code, time window) plus basic text similarity. All merges are reversible with full audit trails.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: FastAPI, azure-cosmos (async), Pydantic, httpx, React 18, TailwindCSS  
**Storage**: Azure Cosmos DB for NoSQL with async SDK  
**Testing**: pytest, pytest-asyncio, pytest-cov, Playwright (E2E)  
**Target Platform**: Linux containers (Docker), cloud-native deployment  
**Project Type**: web (frontend + backend)  
**Performance Goals**: p95 < 300ms for API endpoints, dashboard loads < 3s, support 5x surge volume  
**Constraints**: p95 < 300ms endpoints (constitution mandate), 100ms p95 for point reads, graceful degradation under load  
**Scale/Scope**: Support 50 concurrent agents, 10k tickets/day ingestion, 90-day trend retention, elastic RU scaling

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Implementation Approach |
|-----------|--------|------------------------|
| I. Security-First | ✅ PASS | Input validation on all endpoints; RBAC enforced; PII masking; no hardcoded secrets |
| II. Audit Logging | ✅ PASS | All merge/revert/cluster actions logged with ISO timestamps, actor, affected resources |
| III. Test-First | ✅ PASS | Contract tests for all API endpoints; 80% coverage for clustering/merge logic |
| IV. Modular Architecture | ✅ PASS | Layered architecture: API → Services → Repositories; dependency injection |
| V. Performance Budgets | ✅ PASS | p95 < 300ms for all endpoints; async Cosmos DB operations; performance tests in CI |
| VI. Ruff Linting | ✅ PASS | Ruff configured in pyproject.toml; pre-commit hooks; CI gate |
| VII. SOLID Principles | ✅ PASS | Single-purpose services; interface abstractions; DI throughout |
| VIII. Async Processing | ✅ PASS | asyncio for all I/O; background task workers for clustering |

**Quality Gates Compliance**:
- Ruff Lint: Configured with strict ruleset
- Unit Tests: pytest with 80% coverage minimum
- Contract Tests: OpenAPI-based contract validation
- Performance Tests: Locust load tests in CI
- Security Scan: Bandit + dependency audit
- Code Review: Required for all PRs

## Project Structure

### Documentation (this feature)

```text
specs/001-ticket-dedup-dashboard/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (OpenAPI specs)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── deduptickets/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app entry
│   │   ├── config.py                  # Settings with pydantic-settings
│   │   ├── dependencies.py            # DI container
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── ticket.py              # Ticket entity
│   │   │   ├── cluster.py             # Cluster entity
│   │   │   ├── merge_operation.py     # Merge tracking
│   │   │   ├── spike_alert.py         # Spike detection
│   │   │   ├── audit_entry.py         # Audit log
│   │   │   └── driver.py              # Driver/trend entity
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── ticket.py              # Pydantic DTOs
│   │   │   ├── cluster.py
│   │   │   ├── merge.py
│   │   │   ├── spike.py
│   │   │   └── audit.py
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                # Abstract repository (Cosmos DB client wrapper)
│   │   │   ├── ticket_repo.py         # tickets container operations
│   │   │   ├── cluster_repo.py        # clusters container operations
│   │   │   ├── merge_repo.py          # merges container operations
│   │   │   └── audit_repo.py          # audit container operations
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── clustering_service.py  # Cluster detection logic
│   │   │   ├── merge_service.py       # Merge/revert operations
│   │   │   ├── spike_service.py       # Spike detection
│   │   │   ├── trend_service.py       # Driver/trend analysis
│   │   │   └── audit_service.py       # Audit logging
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── clusters.py
│   │   │   │   ├── merges.py
│   │   │   │   ├── spikes.py
│   │   │   │   ├── trends.py
│   │   │   │   ├── tickets.py
│   │   │   │   └── audit.py
│   │   │   └── middleware/
│   │   │       ├── __init__.py
│   │   │       └── audit_middleware.py
│   │   ├── workers/
│   │   │   ├── __init__.py
│   │   │   ├── clustering_worker.py   # Background clustering
│   │   │   └── spike_worker.py        # Background spike detection
│   │   └── lib/
│   │       ├── __init__.py
│   │       ├── similarity.py          # Text similarity utils
│   │       └── masking.py             # PII masking utils
│   └── cosmos/
│       ├── __init__.py
│       ├── client.py                  # Async Cosmos client singleton
│       └── setup.py                   # Container creation & indexing policies
├── tests/
│   ├── conftest.py
│   ├── contract/
│   │   ├── test_clusters_api.py
│   │   ├── test_merges_api.py
│   │   └── test_audit_api.py
│   ├── integration/
│   │   ├── test_clustering_flow.py
│   │   └── test_merge_revert_flow.py
│   └── unit/
│       ├── test_clustering_service.py
│       ├── test_merge_service.py
│       └── test_similarity.py
├── pyproject.toml
└── Dockerfile

frontend/
├── src/
│   ├── components/
│   │   ├── clusters/
│   │   │   ├── ClusterList.tsx
│   │   │   ├── ClusterCard.tsx
│   │   │   ├── ClusterDetail.tsx
│   │   │   └── MergeDialog.tsx
│   │   ├── spikes/
│   │   │   ├── SpikeAlert.tsx
│   │   │   └── SpikeDrilldown.tsx
│   │   ├── trends/
│   │   │   ├── TopDrivers.tsx
│   │   │   └── TrendChart.tsx
│   │   ├── audit/
│   │   │   └── AuditLog.tsx
│   │   └── shared/
│   │       ├── ConfidenceBadge.tsx
│   │       └── TicketPreview.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── ClustersPage.tsx
│   │   ├── SpikesPage.tsx
│   │   ├── TrendsPage.tsx
│   │   └── AuditPage.tsx
│   ├── services/
│   │   ├── api.ts
│   │   ├── clusterService.ts
│   │   └── spikeService.ts
│   ├── hooks/
│   │   └── useClusters.ts
│   ├── App.tsx
│   └── main.tsx
├── tests/
│   └── e2e/
│       └── merge-flow.spec.ts
├── package.json
├── vite.config.ts
└── Dockerfile
```

**Structure Decision**: Web application structure selected. Backend handles clustering logic, merge operations, and API. Frontend provides the agent dashboard UI. Both deployed as separate containers.

## Complexity Tracking

> No constitution violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | — | — |

## Milestones (v1)

### Milestone 1: Foundation (Week 1-2)
- Project scaffolding (backend + frontend)
- Azure Cosmos DB containers and indexing policies
- Core document models: Ticket, Cluster, MergeOperation, AuditEntry
- Async Cosmos client with connection pooling
- Basic API structure with health check
- Ruff + pytest + pre-commit configured

### Milestone 2: Clustering Core (Week 3-4)
- Ticket ingestion endpoint
- Clustering service (field matching + text similarity)
- Cluster API endpoints (list, detail)
- Background clustering worker
- Cluster UI: list and detail views

### Milestone 3: Merge & Revert (Week 5-6)
- Merge service with snapshot preservation
- Revert service with full restoration
- Merge/revert API endpoints
- Audit logging for all operations
- Merge UI with conflict warnings

### Milestone 4: Spikes & Trends (Week 7-8)
- Spike detection service
- Trend aggregation service
- Spike/trend API endpoints
- Dashboard UI with spike alerts
- Top drivers and trend charts

### Milestone 5: Polish & Performance (Week 9-10)
- Performance optimization
- Load testing (Locust)
- E2E tests (Playwright)
- Documentation (quickstart.md)
- Security hardening review
