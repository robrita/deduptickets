# DedupTickets Backend

FastAPI backend for the Ticket Deduplication & Clustering Dashboard.

## Overview

This service provides APIs for:
- **Ticket ingestion** with automatic clustering
- **Cluster management** (view, merge, dismiss)
- **Merge operations** with revert capability
- **Spike detection** for volume anomalies
- **Trend analysis** for top drivers and growth patterns
- **Audit trail** for all operations

## Tech Stack

- **Python 3.12+**
- **FastAPI** - Async web framework
- **Pydantic v2** - Data validation and settings
- **Azure Cosmos DB** - NoSQL database (async SDK)
- **Ruff** - Linting and formatting
- **Pytest** - Testing framework with pytest-asyncio

## Project Structure

```
backend/
├── src/deduptickets/
│   ├── api/
│   │   ├── middleware/       # Caching, audit middleware
│   │   └── routes/           # API endpoints
│   ├── cosmos/               # Database client and setup
│   ├── lib/                  # Utility libraries (similarity)
│   ├── models/               # Pydantic domain models
│   ├── repositories/         # Data access layer
│   ├── schemas/              # Request/Response DTOs
│   ├── services/             # Business logic
│   ├── workers/              # Background workers
│   ├── config.py             # Configuration settings
│   ├── dependencies.py       # Dependency injection
│   ├── exceptions.py         # Custom exceptions
│   └── main.py               # FastAPI application entry
├── tests/
│   ├── contract/             # API contract tests
│   ├── integration/          # Integration tests
│   ├── unit/                 # Unit tests
│   ├── conftest.py           # Test fixtures
│   └── utils.py              # Test utilities
└── pyproject.toml            # Project configuration
```

## Quick Start

### Prerequisites

- Python 3.12+
- Azure Cosmos DB Emulator (for local development)

### Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies (including dev dependencies)
pip install -e ".[dev]"

# Copy environment configuration
cp .env.example .env
# Edit .env with your Cosmos DB settings

# Initialize Cosmos DB containers
python -m src.deduptickets.cosmos.setup

# Start development server
uvicorn src.deduptickets.main:app --reload --port 8000
```

### Development Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/deduptickets --cov-report=html

# Run specific test type
pytest tests/unit/
pytest tests/contract/
pytest tests/integration/

# Linting
ruff check .
ruff check --fix .

# Formatting
ruff format .

# Type checking
mypy src/
```

## API Endpoints

### Health Check
- `GET /health` - Service health status

### Tickets
- `POST /api/v1/tickets` - Ingest ticket (triggers clustering)
- `GET /api/v1/tickets` - List tickets
- `GET /api/v1/tickets/{id}` - Get ticket by ID

### Clusters
- `GET /api/v1/clusters` - List clusters (filter by status)
- `GET /api/v1/clusters/{id}` - Get cluster with member tickets
- `POST /api/v1/clusters/{id}/dismiss` - Dismiss cluster
- `DELETE /api/v1/clusters/{id}/members/{ticket_id}` - Remove ticket from cluster

### Merges
- `POST /api/v1/merges` - Execute merge operation
- `GET /api/v1/merges` - List merge operations
- `GET /api/v1/merges/{id}` - Get merge details
- `POST /api/v1/merges/{id}/revert` - Revert a merge

### Spikes
- `GET /api/v1/spikes` - List spike alerts
- `GET /api/v1/spikes/{id}` - Get spike details
- `GET /api/v1/spikes/active/count` - Count active spikes
- `POST /api/v1/spikes/{id}/acknowledge` - Acknowledge spike
- `POST /api/v1/spikes/{id}/resolve` - Resolve spike

### Trends
- `GET /api/v1/trends/top-drivers` - Top issue drivers
- `GET /api/v1/trends/fastest-growing` - Fastest growing categories
- `GET /api/v1/trends/most-duplicated` - Most duplicated products
- `GET /api/v1/trends/summary` - Summary statistics

### Audit
- `GET /api/v1/audit` - List audit entries (filterable)
- `GET /api/v1/audit/{id}` - Get audit entry
- `GET /api/v1/audit/entity/{type}/{id}` - Get entity audit trail
- `POST /api/v1/audit/search` - Advanced audit search

## Configuration

Environment variables (see `.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `COSMOS_ENDPOINT` | Cosmos DB endpoint URL | `https://localhost:8081` |
| `COSMOS_KEY` | Cosmos DB primary key | (emulator key) |
| `COSMOS_DATABASE` | Database name | `deduptickets-db` |
| `COSMOS_VERIFY_SSL` | Verify SSL certificates | `false` (dev) |
| `API_KEY` | API authentication key | (required) |
| `LOG_LEVEL` | Logging level | `INFO` |
| `CLUSTERING_INTERVAL_SECONDS` | Clustering worker interval | `300` |
| `SPIKE_DETECTION_INTERVAL_SECONDS` | Spike detection interval | `900` |

## Architecture

### Data Access Pattern

```
Request → Route → Service → Repository → Cosmos DB
                     ↓
                Audit Service
```

### Partition Keys

| Container | Partition Key Pattern | Purpose |
|-----------|----------------------|---------|
| tickets | `{region}\|{year-month}` | Geographic + temporal locality |
| clusters | `{region}\|{year-month}` | Collocate with tickets |
| merges | `{cluster_pk}` | Collocate with cluster |
| audit | `{entityType}\|{year-month}` | Entity-based querying |
| spikes | `{region}\|{year-month}` | Regional spike analysis |
| baselines | `{fieldName}\|{fieldValue}` | Fast baseline lookups |

### Clustering Algorithm

1. Group tickets by exact match fields (transactionId, merchant, category)
2. Apply time window filter (within 1 hour)
3. Calculate text similarity (TF-IDF cosine) for summary/description
4. Assign confidence: High (≥0.8), Medium (0.5-0.8), Low (<0.5)
5. Create/update cluster with matching signals

### Spike Detection

1. Calculate hourly ticket volume per field (category, region, etc.)
2. Compare against rolling baseline (Welford's algorithm)
3. Flag anomalies exceeding threshold:
   - Low: 150-200%
   - Medium: 200-300%
   - High: 300%+

## Testing

### Unit Tests

Test business logic in isolation with mocked repositories.

```python
async def test_cluster_by_transaction_id():
    service = ClusteringService(mock_repo)
    result = await service.detect_clusters(tickets)
    assert len(result) == 1
```

### Contract Tests

Validate API responses match OpenAPI spec.

```python
async def test_list_clusters_returns_paginated_response(client):
    response = await client.get("/clusters")
    assert "items" in response.json()
    assert "pagination" in response.json()
```

### Integration Tests

End-to-end flows with real Cosmos DB emulator.

```python
async def test_ingest_cluster_merge_flow():
    # Ingest tickets → verify cluster → merge → verify linked
```

## Contributing

1. Write tests first (TDD)
2. Run linting: `ruff check --fix .`
3. Run formatting: `ruff format .`
4. Ensure all tests pass: `pytest`
5. Submit PR with clear description

## License

Proprietary - Internal use only
