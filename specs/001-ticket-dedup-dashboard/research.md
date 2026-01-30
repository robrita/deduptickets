# Research: Ticket Deduplication & Clustering Dashboard

**Feature**: 001-ticket-dedup-dashboard  
**Date**: 2026-01-27  
**Purpose**: Resolve technical unknowns and document key decisions

## 1. Clustering Algorithm Approach

### Decision
Use a hybrid approach combining **exact field matching** (transaction ID, error code, time window) with **fuzzy text similarity** (TF-IDF + cosine similarity) for ticket clustering.

### Rationale
- Exact matching provides high-confidence clusters with clear explainability
- Text similarity catches near-duplicates without identical metadata
- Hybrid approach balances precision (fewer false positives) with recall (catching real duplicates)
- Constitution requires explainability; field matching provides clear "why" for each cluster

### Alternatives Considered
| Alternative | Rejected Because |
|-------------|------------------|
| ML embeddings (BERT, sentence transformers) | Higher complexity, less explainable, requires GPU resources |
| Simple keyword matching | Too many false positives, poor quality |
| Graph-based clustering | Over-engineered for v1; consider for v2 if scale demands |

### Implementation Notes
- Use scikit-learn's TfidfVectorizer for text similarity
- Configurable similarity threshold (default 0.7)
- Priority: exact match > time window match > text similarity
- Confidence levels: High (exact match), Medium (time + partial match), Low (text only)

---

## 2. Database Choice: Azure Cosmos DB for NoSQL

### Decision
Use **Azure Cosmos DB for NoSQL** with the async Python SDK for document storage.

### Rationale
- Elastic scale with automatic RU-based throughput management
- Low-latency global distribution capabilities (single-digit ms reads)
- Native JSON document storage aligns with ticket data structure
- Hierarchical Partition Keys (HPK) enable flexible querying by region + time
- Built-in TTL for automatic audit log retention
- Change feed for real-time clustering triggers
- Azure ecosystem integration for enterprise deployments

### Alternatives Considered
| Alternative | Rejected Because |
|-------------|------------------|
| PostgreSQL | Less elastic scaling; requires manual partitioning |
| MongoDB Atlas | Additional vendor; Cosmos provides equivalent features |
| DynamoDB | AWS-specific; team prefers Azure ecosystem |

### Implementation Notes
- Use `azure-cosmos` async SDK with singleton client pattern
- Partition Key: `pk` = `{region}|{year-month}` (e.g., "PH|2025-12") for even distribution
- Composite indexes for common query patterns (status + createdAt)
- Reuse CosmosClient instance across requests (never recreate)
- Log diagnostics when latency exceeds thresholds or errors occur
- Use change feed for triggering clustering on new tickets

---

## 3. API Framework: FastAPI

### Decision
Use **FastAPI** with Pydantic v2 for the backend API.

### Rationale
- Native async support aligns with constitution principle VIII
- Automatic OpenAPI documentation
- Pydantic v2 provides fast validation with clear error messages
- Excellent performance characteristics (p95 < 300ms achievable)
- Dependency injection built-in

### Alternatives Considered
| Alternative | Rejected Because |
|-------------|------------------|
| Django REST Framework | Sync by default; async support less mature |
| Flask | No built-in async; more boilerplate |
| Litestar | Less community adoption; fewer battle-tested examples |

### Implementation Notes
- Use lifespan context for startup/shutdown
- Structured exception handlers for consistent error responses
- Use BackgroundTasks for non-blocking audit logging
- APIRouter per domain (clusters, merges, spikes, etc.)

---

## 4. Frontend Framework: React + Vite

### Decision
Use **React 18** with Vite for the dashboard frontend.

### Rationale
- Component-based architecture for modular UI
- Large ecosystem of UI libraries (shadcn/ui recommended)
- TypeScript support for type safety
- Vite provides fast development experience
- React Query for server state management

### Alternatives Considered
| Alternative | Rejected Because |
|-------------|------------------|
| Vue.js | Team familiarity with React higher |
| Next.js | SSR not needed for internal dashboard |
| Svelte | Smaller ecosystem; less hiring pool |

### Implementation Notes
- Use React Query (TanStack Query) for API calls
- TailwindCSS for styling (utility-first, fast iteration)
- shadcn/ui for component primitives
- React Router for navigation

---

## 5. Background Task Processing

### Decision
Use **asyncio background workers** with optional **Celery + Redis** for scale-out.

### Rationale
- Clustering is CPU-light but I/O-heavy (DB reads)
- asyncio workers sufficient for v1 scale (10k tickets/day)
- Celery provides horizontal scaling path if needed
- Constitution mandates async processing for I/O operations

### Alternatives Considered
| Alternative | Rejected Because |
|-------------|------------------|
| APScheduler | Less suitable for distributed task execution |
| Dramatiq | Less adoption than Celery |
| AWS Lambda | Adds infrastructure complexity |

### Implementation Notes
- Phase 1: In-process asyncio task runner
- Phase 2 (if needed): Celery with Redis broker
- Clustering runs every 5 minutes on new tickets
- Spike detection runs every 15 minutes

---

## 6. Merge/Revert Data Model

### Decision
Store **complete ticket snapshots** before merge to enable full restoration.

### Rationale
- Constitution requires 100% reversibility (FR-011, FR-012)
- Snapshot approach guarantees zero data loss on revert
- Simple to implement and reason about
- Storage cost acceptable (JSONB, compress if needed)

### Alternatives Considered
| Alternative | Rejected Because |
|-------------|------------------|
| Event sourcing | Over-engineered for v1; high implementation cost |
| Delta/diff storage | Complex merge logic; risk of incomplete restoration |
| Soft deletes only | Doesn't preserve pre-merge ticket state properly |

### Implementation Notes
- MergeOperation document stores: primaryTicketId, secondaryTicketIds, mergeBehavior, originalStates (embedded)
- originalStates contains full ticket snapshots for each merged ticket
- Revert reads snapshots and upserts restored tickets to container
- Transactional batch for atomic merge/revert within same partition
- Audit entry stored separately with reference to merge operation ID

---

## 7. Spike Detection Algorithm

### Decision
Use **rolling window baseline comparison** with configurable thresholds.

### Rationale
- Compare current hour volume to average of same hour over past 7 days
- Percentage increase threshold (default 200%) triggers spike alert
- Field-grouped aggregations detect category/channel/partner-specific spikes
- Simple, explainable, and performant

### Alternatives Considered
| Alternative | Rejected Because |
|-------------|------------------|
| ML anomaly detection | Overkill for v1; requires training data |
| Static thresholds | Doesn't adapt to normal volume patterns |
| Real-time streaming (Kafka) | Infrastructure overhead not justified for v1 |

### Implementation Notes
- Baseline table: hourly aggregates by field combination
- Spike worker compares current rolling hour to baseline
- Severity levels: Low (150-200%), Medium (200-300%), High (300%+)
- Drill-down via cluster_id foreign keys

---

## 8. Authentication Approach (v1)

### Decision
**Authentication deferred to v1.1**; v1 operates in trusted network with API key validation only.

### Rationale
- User explicitly stated "auth not supported for now"
- Reduces v1 scope while maintaining security boundary
- API key validates requests are from authorized systems
- RBAC stubs prepared for v1.1 integration

### Alternatives Considered
| Alternative | Rejected Because |
|-------------|------------------|
| Full OAuth2/OIDC | Scope creep for v1 |
| Session-based auth | Adds state complexity |

### Implementation Notes
- X-API-Key header validation middleware
- Configurable via environment variable
- Stub user context for audit logging (system user)
- RBAC interfaces defined but not enforced in v1

---

## 9. PII Masking Strategy

### Decision
Apply **field-level masking** for sensitive data in API responses.

### Rationale
- Constitution requires minimizing visible PII (FR-022)
- Masking at API layer preserves raw data in DB for operations
- Configurable mask patterns per field type

### Alternatives Considered
| Alternative | Rejected Because |
|-------------|------------------|
| Encryption at rest only | Doesn't protect in-transit or in-UI |
| Tokenization | Adds infrastructure complexity |
| Field exclusion | Reduces operational visibility |

### Implementation Notes
- Mask email: j***@example.com
- Mask phone: ***-***-1234
- Mask transaction ID: first 4 + last 4 visible
- Masking applied in Pydantic response serializers

---

## 10. Test Strategy

### Decision
Three-tier testing aligned with constitution requirements.

### Rationale
- Contract tests validate API behavior per OpenAPI spec
- Integration tests verify clustering/merge flows end-to-end
- Unit tests focus on business logic (clustering, similarity)
- Constitution mandates TDD for critical logic (Principle III)

### Implementation Notes

**Unit Tests** (pytest):
- clustering_service: field matching, similarity scoring
- merge_service: snapshot creation, revert logic
- similarity: text preprocessing, cosine calculations
- Target: 80% coverage for services/

**Contract Tests** (pytest + httpx):
- All API endpoints tested against OpenAPI schema
- Response structure validation
- Error response format verification

**Integration Tests** (pytest + Azure Cosmos DB Emulator):
- Full clustering flow: ingest → cluster → review
- Merge → revert → verify restoration
- Spike detection with simulated volume surge
- Cross-partition query performance validation

**E2E Tests** (Playwright):
- Merge workflow UI flow
- Cluster review and dismissal
- Audit log visibility

**Performance Tests** (Locust):
- Cluster list endpoint: 100 concurrent users, p95 < 300ms
- Merge operation: 10 concurrent merges, p95 < 300ms

---

## Summary: Key Decisions

| Area | Decision | Confidence |
|------|----------|------------|
| Clustering | Hybrid: exact fields + TF-IDF text similarity | High |
| Database | Azure Cosmos DB for NoSQL + async SDK | High |
| API Framework | FastAPI + Pydantic v2 | High |
| Frontend | React 18 + Vite + TailwindCSS | High |
| Background Tasks | asyncio workers (Celery for scale) | Medium |
| Merge Strategy | Full snapshots for reversibility | High |
| Spike Detection | Rolling window baseline comparison | High |
| Auth | API key only (v1); deferred RBAC | High |
| PII Handling | Field-level masking in response serializers | High |
| Testing | TDD: unit + contract + integration + E2E | High |

All NEEDS CLARIFICATION items from Technical Context have been resolved.
