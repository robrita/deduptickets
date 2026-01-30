# Tasks: Ticket Deduplication & Clustering Dashboard

**Feature**: 001-ticket-dedup-dashboard  
**Generated**: 2026-01-27  
**Input**: plan.md, spec.md, data-model.md, contracts/openapi.yaml, research.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, etc.)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, tooling, and basic structure

- [x] T001 Create backend project structure per plan.md in backend/
- [x] T002 Initialize Python 3.12 project with pyproject.toml including FastAPI, azure-cosmos, pydantic, pytest dependencies
- [x] T003 [P] Configure Ruff linting with strict ruleset in pyproject.toml
- [x] T004 [P] Configure pytest with pytest-asyncio in pyproject.toml
- [x] T005 [P] Create pre-commit hooks configuration in .pre-commit-config.yaml
- [x] T006 Create frontend project structure with Vite + React 18 + TypeScript in frontend/
- [x] T007 [P] Configure TailwindCSS in frontend/tailwind.config.js
- [x] T008 [P] Configure ESLint + Prettier for frontend in frontend/.eslintrc.cjs
- [x] T009 Create docker-compose.yaml with Cosmos DB Emulator and backend/frontend services
- [x] T010 Create backend/.env.example with Cosmos DB connection variables per quickstart.md
- [x] T011 Create frontend/.env.example with VITE_API_URL variable

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can begin

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Cosmos DB Infrastructure

- [x] T012 Implement async Cosmos client singleton in backend/src/deduptickets/cosmos/client.py
- [x] T013 Implement container setup script with indexing policies in backend/src/deduptickets/cosmos/setup.py
- [x] T014 Create Pydantic settings configuration in backend/src/deduptickets/config.py

### Core Models (All Stories Depend)

- [x] T015 [P] Create Ticket Pydantic model in backend/src/deduptickets/models/ticket.py
- [x] T016 [P] Create Cluster Pydantic model in backend/src/deduptickets/models/cluster.py
- [x] T017 [P] Create MergeOperation Pydantic model in backend/src/deduptickets/models/merge_operation.py
- [x] T018 [P] Create AuditEntry Pydantic model in backend/src/deduptickets/models/audit_entry.py
- [x] T019 [P] Create SpikeAlert Pydantic model in backend/src/deduptickets/models/spike_alert.py
- [x] T020 [P] Create Baseline Pydantic model in backend/src/deduptickets/models/baseline.py

### Request/Response Schemas

- [x] T021 [P] Create Ticket DTOs (TicketCreate, TicketResponse) in backend/src/deduptickets/schemas/ticket.py
- [x] T022 [P] Create Cluster DTOs (ClusterResponse, ClusterDetail) in backend/src/deduptickets/schemas/cluster.py
- [x] T023 [P] Create Merge DTOs (MergeRequest, MergeResponse) in backend/src/deduptickets/schemas/merge.py
- [x] T024 [P] Create Audit DTOs (AuditResponse, AuditListResponse) in backend/src/deduptickets/schemas/audit.py
- [x] T025 [P] Create Spike DTOs (SpikeResponse, SpikeDetail) in backend/src/deduptickets/schemas/spike.py
- [x] T026 [P] Create shared schemas (PaginationMeta, ErrorResponse, HealthResponse) in backend/src/deduptickets/schemas/common.py

### Base Repository Layer

- [x] T027 Implement abstract BaseRepository with Cosmos client wrapper in backend/src/deduptickets/repositories/base.py
- [x] T028 [P] Implement TicketRepository (CRUD, query by transactionId) in backend/src/deduptickets/repositories/ticket.py
- [x] T029 [P] Implement ClusterRepository (CRUD, query by status) in backend/src/deduptickets/repositories/cluster.py
- [x] T030 [P] Implement MergeRepository (CRUD, query by clusterId) in backend/src/deduptickets/repositories/merge.py
- [x] T031 [P] Implement AuditRepository (insert-only, query by resource) in backend/src/deduptickets/repositories/audit.py

### FastAPI Application Core

- [x] T032 Create FastAPI app entry point with lifespan context in backend/src/deduptickets/main.py
- [x] T033 Implement dependency injection container in backend/src/deduptickets/dependencies.py
- [x] T034 [P] Implement health check endpoint in backend/src/deduptickets/routes/health.py
- [x] T035 [P] Implement API key validation middleware in backend/src/deduptickets/dependencies.py
- [x] T036 [P] Implement global exception handlers in backend/src/deduptickets/exceptions.py
- [x] T037 Register all routers in backend/src/deduptickets/main.py

### Audit Service (All Stories Depend)

- [x] T038 Implement AuditService with log_action method in backend/src/deduptickets/repositories/audit.py
- [x] T039 Implement audit middleware for automatic request logging in backend/src/deduptickets/api/middleware/audit_middleware.py

### Test Infrastructure

- [x] T040 Create pytest conftest with Cosmos client fixtures in backend/tests/conftest.py
- [x] T041 [P] Create test utilities for sample ticket generation in backend/tests/utils.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Review and Merge Duplicate Tickets (Priority: P1) 🎯 MVP

**Goal**: Support agents can view system-suggested clusters and merge duplicate tickets into a primary

**Independent Test**: Ingest sample tickets with matching fields → verify cluster appears → perform merge → verify tickets linked

**FR Coverage**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-010, FR-020, FR-021, FR-025

### Backend: Clustering Logic

- [x] T042 [US1] Implement text similarity utilities (TF-IDF + cosine) in backend/src/deduptickets/lib/similarity.py
- [x] T043 [US1] Implement ClusteringService with real-time cluster detection in backend/src/deduptickets/services/clustering_service.py
  - Exact field matching: transactionId, merchant, category
  - Time window matching: tickets within 1 hour
  - Text similarity: configurable threshold (default 0.7)
  - Confidence assignment: High/Medium/Low
  - Summary generation from matching signals
- [x] T044 [US1] Implement cluster creation on ticket ingestion (synchronous, <30s) in backend/src/deduptickets/services/clustering_service.py

### Backend: Merge Logic

- [x] T045 [US1] Implement MergeService with merge_cluster method in backend/src/deduptickets/services/merge_service.py
  - Creates MergeOperation document with originalStates snapshots
  - Updates secondary tickets with mergedIntoId
  - Updates cluster status to Merged
  - Supports mergeBehavior: KeepLatest, CombineNotes, RetainAll
- [x] T046 [US1] Add optimistic concurrency control for merge conflicts in backend/src/deduptickets/services/merge_service.py

### Backend: API Endpoints

- [x] T047 [P] [US1] Implement POST /tickets endpoint with clustering trigger in backend/src/deduptickets/api/routes/tickets.py
- [x] T048 [P] [US1] Implement GET /tickets and GET /tickets/{id} endpoints in backend/src/deduptickets/api/routes/tickets.py
- [x] T049 [P] [US1] Implement GET /clusters and GET /clusters/{id} endpoints in backend/src/deduptickets/api/routes/clusters.py
- [x] T050 [P] [US1] Implement POST /clusters/{id}/dismiss endpoint in backend/src/deduptickets/api/routes/clusters.py
- [x] T051 [P] [US1] Implement DELETE /clusters/{id}/members/{ticket_id} endpoint in backend/src/deduptickets/api/routes/clusters.py
- [x] T052 [US1] Implement POST /merges endpoint in backend/src/deduptickets/api/routes/merges.py
- [x] T053 [P] [US1] Implement GET /merges and GET /merges/{id} endpoints in backend/src/deduptickets/api/routes/merges.py

### Frontend: Cluster List & Detail

- [x] T054 [P] [US1] Create API client service in frontend/src/services/api.ts
- [x] T055 [P] [US1] Create clusterService with list/get/dismiss methods in frontend/src/services/clusterService.ts
- [x] T056 [P] [US1] Create ConfidenceBadge component (High/Medium/Low styling) in frontend/src/components/shared/ConfidenceBadge.tsx
- [x] T057 [P] [US1] Create TicketPreview component for cluster members in frontend/src/components/shared/TicketPreview.tsx
- [x] T058 [US1] Create ClusterCard component with summary and signals in frontend/src/components/clusters/ClusterCard.tsx
- [x] T059 [US1] Create ClusterList component with filtering in frontend/src/components/clusters/ClusterList.tsx
- [x] T060 [US1] Create ClusterDetail component with member tickets in frontend/src/components/clusters/ClusterDetail.tsx

### Frontend: Merge Dialog

- [x] T061 [US1] Create MergeDialog component with primary selection and behavior choice in frontend/src/components/clusters/MergeDialog.tsx
- [x] T062 [US1] Create useClusters hook with React Query in frontend/src/hooks/useClusters.ts
- [x] T063 [US1] Create ClustersPage with list view and detail panel in frontend/src/pages/ClustersPage.tsx
- [x] T064 [US1] Add cluster routes to App.tsx in frontend/src/App.tsx

### Unit Tests

- [x] T065 [P] [US1] Unit test similarity scoring in backend/tests/unit/test_similarity.py
- [x] T066 [P] [US1] Unit test clustering service logic in backend/tests/unit/test_clustering_service.py
- [x] T067 [P] [US1] Unit test merge service logic in backend/tests/unit/test_merge_service.py

### Integration Tests

- [x] T068 [US1] Integration test: ingest → cluster flow in backend/tests/integration/test_clustering_flow.py
- [x] T069 [US1] Integration test: cluster → merge flow in backend/tests/integration/test_merge_flow.py

**Checkpoint**: User Story 1 complete - agents can review clusters and merge duplicates. MVP functional.

---

## Phase 4: User Story 2 - Revert a Merge (Priority: P2)

**Goal**: Agents/leads can undo merge operations and restore original tickets

**Independent Test**: Perform merge → modify primary → revert → verify original tickets restored with warning about conflicts

**FR Coverage**: FR-011, FR-012, FR-013, FR-026

### Backend: Revert Logic

- [x] T070 [US2] Implement revert_merge method in MergeService in backend/src/deduptickets/services/merge_service.py
  - Restores tickets from originalStates snapshots
  - Updates MergeOperation status to Reverted
  - Updates cluster status back to Pending (optional)
  - Logs revert action to audit

- [x] T071 [US2] Implement conflict detection for post-merge updates in backend/src/deduptickets/services/merge_service.py
  - Compare current ticket state to snapshot
  - Return RevertConflictResponse if primary was modified
  - Preserve post-merge changes on restored primary if requested

### Backend: API Endpoints

- [x] T072 [US2] Implement POST /merges/{id}/revert endpoint in backend/src/deduptickets/api/routes/merges.py
  - Returns 409 if already reverted
  - Returns 422 with conflicts if primary modified

### Frontend: Revert UI

- [x] T073 [US2] Create RevertConfirmDialog with conflict warnings in frontend/src/components/merges/RevertConfirmDialog.tsx
- [x] T074 [US2] Add revert button to merge history view in frontend/src/components/merges/MergeHistoryItem.tsx
- [x] T075 [US2] Create MergesPage with merge history and revert actions in frontend/src/pages/MergesPage.tsx

### Tests

- [x] T076 [P] [US2] Unit test revert logic in backend/tests/unit/test_merge_service.py
- [x] T077 [US2] Integration test: merge → revert → verify restoration in backend/tests/integration/test_merge_revert_flow.py

**Checkpoint**: User Story 2 complete - merges are fully reversible with conflict handling

---

## Phase 5: User Story 3 - Detect and Investigate Ticket Spikes (Priority: P3)

**Goal**: Team leads can see real-time spike alerts and drill down to affected tickets

**Independent Test**: Simulate 300% volume increase for one merchant → verify spike alert appears → drill down to clusters

**FR Coverage**: FR-014, FR-015, FR-016

### Backend: Baseline & Spike Detection

- [x] T078 [P] [US3] Implement SpikeRepository (CRUD, query active) in backend/src/deduptickets/repositories/spike_repo.py
- [x] T079 [P] [US3] Implement BaselineRepository (upsert, query by field) in backend/src/deduptickets/repositories/baseline_repo.py
- [x] T080 [US3] Implement SpikeService with baseline comparison in backend/src/deduptickets/services/spike_service.py
  - Compare current hour volume to historical baseline
  - Threshold configurable via environment (default 200%)
  - Severity: Low (150-200%), Medium (200-300%), High (300%+)
  - Link affected clusters to spike

- [x] T081 [US3] Implement spike detection background worker in backend/src/deduptickets/workers/spike_worker.py
  - Runs every 15 minutes
  - Aggregates ticket volume by configured fields (category, channel, region, merchant, subcategory, severity)
  - Creates/updates SpikeAlert documents

### Backend: API Endpoints

- [x] T082 [P] [US3] Implement GET /spikes and GET /spikes/{id} endpoints in backend/src/deduptickets/api/routes/spikes.py
- [x] T083 [P] [US3] Implement POST /spikes/{id}/acknowledge endpoint in backend/src/deduptickets/api/routes/spikes.py
- [x] T084 [P] [US3] Implement POST /spikes/{id}/resolve endpoint in backend/src/deduptickets/api/routes/spikes.py

### Frontend: Spike Dashboard

- [x] T085 [P] [US3] Create spikeService with list/get/acknowledge methods in frontend/src/services/spikeService.ts
- [x] T086 [US3] Create SpikeAlert component with severity indicator in frontend/src/components/spikes/SpikeAlert.tsx
- [x] T087 [US3] Create SpikeDrilldown component with linked clusters in frontend/src/components/spikes/SpikeDrilldown.tsx
- [x] T088 [US3] Create SpikesPage with active alerts list in frontend/src/pages/SpikesPage.tsx

### Tests

- [x] T089 [P] [US3] Unit test spike detection logic in backend/tests/unit/test_spike_service.py
- [x] T090 [US3] Integration test: volume surge → spike detection in backend/tests/integration/test_spike_detection.py

**Checkpoint**: User Story 3 complete - team leads can monitor and investigate spikes

---

## Phase 6: User Story 4 - View Top Drivers and Trends (Priority: P4)

**Goal**: Leads/PMs can see recurring themes and trend patterns

**Independent Test**: Accumulate cluster data → verify top drivers ranked correctly → verify growth calculations

**FR Coverage**: FR-017, FR-018, FR-019

### Backend: Trend Analysis

- [x] T091 [US4] Implement Driver model in backend/src/deduptickets/models/driver.py
- [x] T092 [US4] Create Driver DTOs in backend/src/deduptickets/schemas/driver.py
- [x] T093 [US4] Implement TrendService with aggregation methods in backend/src/deduptickets/services/trend_service.py
  - top_drivers: ranked by cluster count
  - fastest_growing: week-over-week growth %
  - most_duplicated: tickets per cluster ratio

### Backend: API Endpoints

- [x] T094 [P] [US4] Implement GET /trends/top-drivers endpoint in backend/src/deduptickets/api/routes/trends.py
- [x] T095 [P] [US4] Implement GET /trends/fastest-growing endpoint in backend/src/deduptickets/api/routes/trends.py
- [x] T096 [P] [US4] Implement GET /trends/most-duplicated endpoint in backend/src/deduptickets/api/routes/trends.py

### Frontend: Trend Views

- [x] T097 [P] [US4] Create trendService with trend API calls in frontend/src/services/trendService.ts
- [x] T098 [US4] Create TopDrivers component with ranked list in frontend/src/components/trends/TopDrivers.tsx
- [x] T099 [US4] Create TrendChart component (simple bar/line) in frontend/src/components/trends/TrendChart.tsx
- [x] T100 [US4] Create TrendsPage with all trend views in frontend/src/pages/TrendsPage.tsx

### Tests

- [x] T101 [P] [US4] Unit test trend aggregation logic in backend/tests/unit/test_trend_service.py

**Checkpoint**: User Story 4 complete - trend analysis available for strategic decisions

---

## Phase 7: User Story 5 - Audit Trail for All Actions (Priority: P5)

**Goal**: Ops managers can search and review complete action history

**Independent Test**: Perform various actions → search audit by ticket/actor/action → verify complete history

**FR Coverage**: FR-025, FR-026, FR-027, FR-028

### Backend: Audit Search

- [x] T102 [US5] Implement audit search with filtering in AuditRepository in backend/src/deduptickets/repositories/audit_repo.py
  - Filter by actionType, actorId, resourceType, resourceId
  - Date range filtering
  - Pagination support

### Backend: API Endpoints

- [x] T103 [P] [US5] Implement GET /audit endpoint with filters in backend/src/deduptickets/api/routes/audit.py
- [x] T104 [P] [US5] Implement GET /audit/{id} endpoint in backend/src/deduptickets/api/routes/audit.py

### Frontend: Audit Log View

- [x] T105 [P] [US5] Create auditService with search method in frontend/src/services/auditService.ts
- [x] T106 [US5] Create AuditLog component with filters and pagination in frontend/src/components/audit/AuditLog.tsx
- [x] T107 [US5] Create AuditPage with search interface in frontend/src/pages/AuditPage.tsx

### Tests

- [x] T108 [US5] Integration test: actions → audit search in backend/tests/integration/test_audit_trail.py

**Checkpoint**: User Story 5 complete - full auditability for compliance

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Performance, quality, and documentation improvements

### Dashboard Home

- [x] T109 [P] Create Dashboard component with summary widgets in frontend/src/pages/Dashboard.tsx
- [x] T110 Update App.tsx with all page routes and navigation in frontend/src/App.tsx

### Performance Optimization

- [x] T111 Add response caching headers for list endpoints in backend/src/deduptickets/api/middleware/cache.py
- [x] T112 Implement Cosmos query optimization (limit, projection) across repositories

### Contract Tests

- [x] T113 [P] Contract test for clusters API per OpenAPI in backend/tests/contract/test_clusters_api.py
- [x] T114 [P] Contract test for merges API per OpenAPI in backend/tests/contract/test_merges_api.py
- [x] T115 [P] Contract test for audit API per OpenAPI in backend/tests/contract/test_audit_api.py

### E2E Tests

- [x] T116 E2E test: merge workflow in frontend/tests/e2e/merge-flow.spec.ts

### Documentation

- [x] T117 [P] Update quickstart.md with final setup steps in specs/001-ticket-dedup-dashboard/quickstart.md
- [x] T118 [P] Create backend/README.md with API documentation
- [x] T119 [P] Create frontend/README.md with component overview

### Finalization (Manual - Requires Dev Environment)

**Note**: These tasks require the development environment to be set up with dependencies installed. Run these manually after setting up the project per quickstart.md.

- [ ] T120 Run ruff check --fix and ruff format on backend/
- [ ] T121 Run eslint --fix on frontend/
- [ ] T122 Validate all tests pass: pytest and npm test
- [ ] T123 Run quickstart.md validation end-to-end

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational) ← BLOCKS ALL USER STORIES
    ↓
┌───────────────────────────────────────────────────────────┐
│ User Stories can proceed in priority order or in parallel │
├───────────────────────────────────────────────────────────┤
│ Phase 3 (US1: P1) → MVP Complete                         │
│ Phase 4 (US2: P2) → Revert capability                    │
│ Phase 5 (US3: P3) → Spike detection                      │
│ Phase 6 (US4: P4) → Trend analysis                       │
│ Phase 7 (US5: P5) → Audit trail                          │
└───────────────────────────────────────────────────────────┘
    ↓
Phase 8 (Polish)
```

### Within Each User Story

1. Backend models/repositories (if new) → parallelizable
2. Backend services → sequential (depend on repos)
3. Backend API endpoints → parallelizable after services
4. Frontend services → parallel with backend endpoints
5. Frontend components → sequential (bottom-up)
6. Tests → parallel after implementation

### Story Inter-Dependencies

| Story | Depends On | Can Start After |
|-------|------------|-----------------|
| US1 (P1) | Foundation only | Phase 2 complete |
| US2 (P2) | US1 (MergeService exists) | T045 complete |
| US3 (P3) | Foundation only | Phase 2 complete |
| US4 (P4) | US1 (cluster data needed) | T043 complete |
| US5 (P5) | Foundation only | Phase 2 complete |

---

## Parallel Execution Examples

### Phase 2: Foundation Models (All Parallel)

```
T015: Create Ticket model
T016: Create Cluster model
T017: Create MergeOperation model
T018: Create AuditEntry model
T019: Create SpikeAlert model
T020: Create Baseline model
```

### Phase 3: US1 API Endpoints (Parallel After Services)

```
T047: POST /tickets
T048: GET /tickets
T049: GET /clusters
T050: POST /clusters/{id}/dismiss
T051: DELETE /clusters/{id}/members/{id}
```

### Phase 3: US1 Frontend Components (Parallel)

```
T054: api.ts
T055: clusterService.ts
T056: ConfidenceBadge.tsx
T057: TicketPreview.tsx
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (~1 day)
2. Complete Phase 2: Foundation (~3 days)
3. Complete Phase 3: User Story 1 (~4 days)
4. **STOP and VALIDATE**: Test cluster + merge flow end-to-end
5. Deploy/demo MVP

**MVP delivery**: ~8 working days

### Incremental Delivery

| Milestone | Stories Included | Cumulative Value |
|-----------|------------------|------------------|
| M1: Foundation | Setup + Foundational | Infrastructure ready |
| M2: MVP | + US1 | Agents can merge duplicates |
| M3: Reversibility | + US2 | Merges are reversible |
| M4: Monitoring | + US3 | Spike detection active |
| M5: Analytics | + US4 | Trend insights available |
| M6: Compliance | + US5 | Full audit trail |
| M7: Polish | Polish phase | Production-ready |

### Total Estimate

- Phase 1-2: ~4 days
- Phase 3 (US1): ~4 days
- Phase 4 (US2): ~2 days
- Phase 5 (US3): ~3 days
- Phase 6 (US4): ~2 days
- Phase 7 (US5): ~2 days
- Phase 8: ~2 days

**Total**: ~19 working days (4 weeks with buffer)

---

## Notes

- All tasks include exact file paths for clarity
- [P] tasks can run in parallel (different files, no dependencies)
- [Story] labels map tasks to user stories for traceability
- FR-009 (soft grouping) and FR-022 (PII masking) deferred to v2 per clarifications
- Cosmos DB Emulator required for integration tests
- Each story checkpoint enables independent validation
