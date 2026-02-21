# DedupTickets Backend

FastAPI backend for the Ticket Deduplication & Clustering Dashboard.

## Overview

This service provides APIs for:
- **Ticket ingestion** with automatic clustering
- **Cluster management** (view, merge, dismiss)
- **Merge operations** with revert capability

## Tech Stack

- **Python 3.12+**
- **FastAPI** - Async web framework
- **Pydantic v2** - Data validation and settings
- **Azure Cosmos DB** - NoSQL database (async SDK)
- **Ruff** - Linting and formatting
- **Pytest** - Testing framework with pytest-asyncio

## Project Structure

```
├── pyproject.toml                # Project configuration
├── Makefile                      # Development commands
├── .env.example                  # Environment template
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── middleware/       # Caching middleware
│   │   │   └── routes/           # API endpoints
│   │   ├── cosmos/               # Database client and setup
│   │   ├── lib/                  # Utility libraries (similarity)
│   │   ├── models/               # Pydantic domain models
│   │   ├── repositories/         # Data access layer
│   │   ├── schemas/              # Request/Response DTOs
│   │   ├── services/             # Business logic
│   │   ├── config.py             # Configuration settings
│   │   ├── dependencies.py       # Dependency injection
│   │   ├── exceptions.py         # Custom exceptions
│   │   └── main.py               # FastAPI application entry
│   ├── tests/
│   │   ├── contract/             # API contract tests
│   │   ├── integration/          # Integration tests
│   │   ├── unit/                 # Unit tests
│   │   ├── conftest.py           # Test fixtures
│   │   └── utils.py              # Test utilities
│   ├── scripts/                  # Data loading and migration scripts
│   └── data/                     # Sample data
└── frontend/                     # React frontend
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
make db-setup

# Start development server
make dev
```

### Development Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend/src --cov-report=html

# Run specific test type
pytest backend/tests/unit/
pytest backend/tests/contract/
pytest backend/tests/integration/

# Linting
ruff check backend/
ruff check --fix backend/

# Formatting
ruff format backend/

# Type checking
mypy backend/src/
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

## Azure Functions Deployment (FastAPI ASGI)

The project runs FastAPI inside Azure Functions using the Python v2 programming model.

- Entry point: `function_app.py`
- FastAPI app: `backend/src/main.py`
- Route prefix: empty (`host.json`) to preserve existing paths (`/health`, `/api/v1/...`)
- Frontend hosting: React build output (`frontend/dist`) served by FastAPI

### Runtime v4 Quick Commands

```bash
# verify Core Tools v4
func --version

# install backend runtime dependencies
pip install -r requirements.txt

# build frontend assets for SPA serving
cd frontend && npm ci && npm run build && cd ..

# start local Functions host
func start --verbose
```

### Local Azure Functions Run

```bash
# Build frontend assets first
cd frontend
npm ci
npm run build
cd ..

# Install backend runtime dependencies
pip install -r requirements.txt

# Start Azure Functions host
func start
```

Smoke tests:
- `GET http://localhost:7071/health`
- `GET http://localhost:7071/api/v1/clusters`
- `GET http://localhost:7071/docs`

### CI/CD (Staging Slot Then Swap)

GitHub Actions workflow: `.github/workflows/deploy-functions.yml`

Flow:
1. Build frontend (`frontend/dist`)
2. Deploy Function App package to staging slot
3. Swap staging slot to production

Required GitHub secrets:
- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `AZURE_RESOURCE_GROUP`
- `AZURE_FUNCTIONAPP_NAME`
- `AZURE_FUNCTIONAPP_STAGING_SLOT`

## Configuration

Environment variables (see `.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `COSMOS_ENDPOINT` | Cosmos DB endpoint URL | `https://localhost:8081` |
| `COSMOS_KEY` | Cosmos DB account key (ignored when AAD is enabled) | (emulator key) |
| `COSMOS_USE_AAD` | Use Microsoft Entra ID instead of account key | `false` |
| `COSMOS_DATABASE` | Database name | `deduptickets` |
| `COSMOS_SSL_VERIFY` | Verify SSL certificates | `false` (dev) |
| `API_KEY` | API authentication key | (required) |
| `LOG_LEVEL` | Logging level | `INFO` |

### Cosmos DB: Local Emulator vs Cloud

#### Option A — Local Emulator (default)

No configuration needed. The defaults connect to the [Azure Cosmos DB Emulator](https://learn.microsoft.com/azure/cosmos-db/emulator):

```env
# .env (optional — these are already the defaults)
COSMOS_ENDPOINT=https://localhost:8081
COSMOS_KEY=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==
COSMOS_SSL_VERIFY=false
```

#### Option B — Cloud Cosmos DB with Account Key

```env
COSMOS_ENDPOINT=https://<your-account>.documents.azure.com:443/
COSMOS_KEY=<your-primary-or-secondary-key>
COSMOS_DATABASE=deduptickets
COSMOS_SSL_VERIFY=true
```

Get the key from **Azure Portal → Cosmos DB account → Keys → Primary Key**.

#### Option C — Cloud Cosmos DB with Microsoft Entra ID (recommended for production)

Uses `DefaultAzureCredential` from `azure-identity` — no secrets to manage.

```env
COSMOS_ENDPOINT=https://<your-account>.documents.azure.com:443/
COSMOS_USE_AAD=true
COSMOS_DATABASE=deduptickets
COSMOS_SSL_VERIFY=true
```

`DefaultAzureCredential` automatically picks up credentials from (in priority order):
1. Environment variables (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET`)
2. Managed Identity (on Azure App Service, Functions, AKS, etc.)
3. Azure CLI (`az login`)
4. VS Code Azure Account extension

#### Azure RBAC Setup for Entra ID

Cosmos DB data-plane access requires the **Cosmos DB Built-in Data Contributor** role (not the generic Azure "Contributor" role).

**Using the included script (recommended):**

```bash
# Assign to the currently signed-in Azure CLI user
make assign-cosmos-role ACCOUNT=mycosmosdb RG=myresourcegroup

# Assign to a specific principal (managed identity, service principal, etc.)
make assign-cosmos-role ACCOUNT=mycosmosdb RG=myresourcegroup PRINCIPAL_ID=<object-id>

# Assign read-only access
make assign-cosmos-role ACCOUNT=mycosmosdb RG=myresourcegroup ROLE=reader
```

Or run the script directly:

```bash
bash scripts/assign_cosmos_role.sh --account mycosmosdb --resource-group myresourcegroup
```

**Using Azure CLI manually:**

```bash
# Get your identity's Object ID
PRINCIPAL_ID=$(az ad signed-in-user show --query id -o tsv)

# Or for a managed identity / service principal:
# PRINCIPAL_ID=$(az identity show -n <identity-name> -g <resource-group> --query principalId -o tsv)

# Assign the Cosmos DB data-plane role
az cosmosdb sql role assignment create \
  --account-name <your-cosmos-account> \
  --resource-group <your-resource-group> \
  --role-definition-name "Cosmos DB Built-in Data Contributor" \
  --principal-id $PRINCIPAL_ID \
  --scope "/"
```

**Using Azure Portal:**

1. Navigate to your Cosmos DB account
2. Go to **Settings → Identity and Access (IAM)** — note: this is the *Cosmos DB data-plane* IAM, not the subscription-level one
3. The built-in roles are:
   - **Cosmos DB Built-in Data Reader** — read-only access
   - **Cosmos DB Built-in Data Contributor** — read/write access (use this one)
4. Assign the role to your user, managed identity, or service principal

## Architecture

### Data Access Pattern

```
Request → Route → Service → Repository → Cosmos DB
```

### Partition Keys

| Container | Partition Key Pattern | Purpose |
|-----------|----------------------|---------|
| tickets | `{year-month}` | Temporal locality |
| clusters | `{year-month}` | Collocate with tickets |
| merges | `{cluster_pk}` | Collocate with cluster |

### Clustering Algorithm

1. Group tickets by exact match fields (transactionId, merchant, category)
2. Apply time window filter (within 1 hour)
3. Calculate text similarity (TF-IDF cosine) for summary/description
4. Assign confidence: High (≥0.8), Medium (0.5-0.8), Low (<0.5)
5. Create/update cluster with matching signals

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
2. Run linting: `ruff check --fix backend/`
3. Run formatting: `ruff format backend/`
4. Ensure all tests pass: `pytest`
5. Submit PR with clear description

## License

Proprietary - Internal use only
