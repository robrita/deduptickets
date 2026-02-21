# Architecture

## Overview

DedupTickets is a ticket deduplication and clustering platform with a FastAPI backend, React frontend, and Azure Cosmos DB for persistence.

**Tech Stack**: Python 3.12+ · FastAPI · Pydantic v2 · Azure Cosmos DB (async SDK) · React + TypeScript · Vite · Tailwind CSS

## Layered Architecture

```
Request → Route → Service → Repository → Cosmos DB
```

Each business domain follows a fixed set of layers with strictly validated dependency directions:

| Layer | Responsibility | Location |
|-------|---------------|----------|
| **Routes** | HTTP handling, request/response mapping | `backend/src/api/routes/` |
| **Schemas** | Request/Response DTOs (Pydantic) | `backend/src/schemas/` |
| **Services** | Business logic, orchestration | `backend/src/services/` |
| **Repositories** | Data access, Cosmos DB operations | `backend/src/repositories/` |
| **Models** | Domain entities (Pydantic) | `backend/src/models/` |
| **Cosmos** | DB client singleton, container setup | `backend/src/cosmos/` |
| **Middleware** | Caching | `backend/src/api/middleware/` |
| **Lib** | Shared utilities (embedding service) | `backend/src/lib/` |

**Dependency rule**: Routes → Services → Repositories → Cosmos. Never skip layers.

## Cosmos DB Containers & Partition Keys

| Container | Partition Key | Purpose |
|-----------|--------------|---------|
| `tickets` | `{year-month}` | Temporal locality |
| `clusters` | `{year-month}` | Collocated with tickets |
| `merges` | `{cluster_pk}` | Collocated with parent cluster |

See `.github/skills/cosmosdb-best-practices/` for Cosmos DB SDK and query optimization rules.

## Core Algorithms

### Clustering (Hybrid Cluster-First Pipeline)

1. Build dedup text from non-PII ticket fields
2. Generate embedding via Azure OpenAI (`text-embedding-3-small`, 1536 dims)
3. Search **clusters** (not tickets) using Cosmos DB `VectorDistance()` on `centroidVector`
4. Score candidates: `0.85×semantic + 0.10×subcategory + 0.03×category + 0.02×time_proximity`
5. Three-tier decision: auto (≥0.92) → add to cluster | review (0.85–0.92) → add + flag | new_cluster (<0.85) → create CANDIDATE
6. ETag-safe cluster updates with incremental centroid: `(old×n + new) / (n+1)`
7. CANDIDATE (1 ticket) → PENDING (2+ tickets) → MERGED or DISMISSED

## Configuration

Key environment variables (see `.env.example` for full list):

| Variable | Description |
|----------|-------------|
| `COSMOS_ENDPOINT` | Cosmos DB endpoint URL |
| `COSMOS_KEY` | Cosmos DB account key (ignored when AAD is enabled) |
| `COSMOS_USE_AAD` | Use Microsoft Entra ID auth instead of account key |
| `COSMOS_DATABASE` | Database name |
| `COSMOS_SSL_VERIFY` | Verify SSL certificates (false for Emulator) |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_API_VERSION` | Azure OpenAI API version (default: 2024-10-21) |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Embedding model deployment name |
| `API_KEY` | API authentication key |
| `LOG_LEVEL` | Logging level |
