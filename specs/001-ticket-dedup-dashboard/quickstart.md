# Quickstart: Ticket Deduplication & Clustering Dashboard

**Feature**: 001-ticket-dedup-dashboard  
**Date**: 2026-01-27

## Prerequisites

- Python 3.12+
- Node.js 20+ (for frontend)
- Azure Cosmos DB Emulator (local development) or Azure Cosmos DB account
- Docker & Docker Compose (optional, for containerized development)

## Quick Setup

### Option A: Docker Compose (Recommended)

```bash
# Clone and enter project
cd deduptickets

# Start all services (includes Cosmos DB Emulator)
docker compose up -d

# Backend available at http://localhost:8000
# Frontend available at http://localhost:3000
# API docs at http://localhost:8000/docs
# Cosmos DB Explorer at https://localhost:8081/_explorer/index.html
```

### Option B: Local Development

#### 1. Cosmos DB Emulator Setup

**Windows (Installed Emulator)**:
```powershell
# Start the emulator (if not running)
Start-Process -FilePath "C:\Program Files\Azure Cosmos DB Emulator\Microsoft.Azure.Cosmos.Emulator.exe"

# Emulator Data Explorer: https://localhost:8081/_explorer/index.html
# Default key: C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==
```

**Docker (Cross-Platform)**:
```bash
# Pull and start Cosmos DB Emulator
docker run -d \
  --name cosmosdb-emulator \
  -p 8081:8081 \
  -p 10251:10251 \
  -p 10252:10252 \
  -p 10253:10253 \
  -p 10254:10254 \
  -e AZURE_COSMOS_EMULATOR_PARTITION_COUNT=10 \
  -e AZURE_COSMOS_EMULATOR_ENABLE_DATA_PERSISTENCE=true \
  mcr.microsoft.com/cosmosdb/linux/azure-cosmos-emulator

# Wait for emulator to start (~2-3 minutes)
# Check status: curl -k https://localhost:8081/_explorer/emulator.pem
```

#### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Initialize Cosmos DB containers
python -m src.deduptickets.cosmos.setup

# Start development server
uvicorn src.deduptickets.main:app --reload --port 8000
```

#### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with your settings

# Start development server
npm run dev
```

## Environment Variables

### Backend (.env)

```bash
# Azure Cosmos DB - Emulator
COSMOS_ENDPOINT=https://localhost:8081
COSMOS_KEY=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==
COSMOS_DATABASE=deduptickets-db

# Azure Cosmos DB - Production (use Azure connection string instead)
# COSMOS_ENDPOINT=https://your-account.documents.azure.com:443
# COSMOS_KEY=your-primary-key

# Security
API_KEY=your-api-key-here
SECRET_KEY=your-secret-key-for-signing

# Logging
LOG_LEVEL=INFO

# Background Workers
CLUSTERING_INTERVAL_SECONDS=300
SPIKE_DETECTION_INTERVAL_SECONDS=900

# SSL (disable for local emulator)
COSMOS_VERIFY_SSL=false
```

### Frontend (.env.local)

```bash
VITE_API_URL=http://localhost:8000/api/v1
VITE_API_KEY=your-api-key-here
```

## Verify Installation

### 1. Health Check

```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy","version":"1.0.0","database":"connected",...}
```

### 2. API Documentation

Open http://localhost:8000/docs for interactive Swagger UI.

### 3. Ingest Sample Ticket

```bash
curl -X POST http://localhost:8000/api/v1/tickets \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "ticketNumber": "GCASH-202512000123",
    "summary": "Instapay transfer failed but amount was deducted",
    "description": "I tried sending to BPI via Instapay. It failed but my balance went down.",
    "status": "Open",
    "priority": "High",
    "channel": "InApp",
    "category": "Transfers",
    "subcategory": "BankTransferFailed",
    "customerId": "CUST-0098123",
    "region": "NCR",
    "city": "Makati",
    "transactionId": "TXN-88123-XYZ",
    "amount": 2500.00,
    "currency": "PHP",
    "merchant": "BPI"
  }'
```

### 4. List Clusters

```bash
curl http://localhost:8000/api/v1/clusters \
  -H "X-API-Key: your-api-key-here"
```

## Running Tests

### Backend Tests

```bash
cd backend

# Run all tests (uses Cosmos DB Emulator)
pytest

# Run with coverage
pytest --cov=src/deduptickets --cov-report=html

# Run specific test categories
pytest tests/unit/           # Unit tests only
pytest tests/contract/       # Contract tests only
pytest tests/integration/    # Integration tests (requires Emulator)

# Run with performance benchmarks
pytest --benchmark-only
```

### Frontend Tests

```bash
cd frontend

# Run unit tests
npm test

# Run E2E tests (requires backend running)
npm run test:e2e
```

### Linting & Formatting

```bash
cd backend

# Check linting
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Format code
ruff format .

# Type checking
mypy src/
```

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Write Tests First (TDD)

Per constitution principle III, write tests before implementation:

```python
# tests/unit/test_clustering_service.py
async def test_cluster_by_transaction_id():
    """Tickets with same transaction_id should cluster."""
    tickets = [
        Ticket(transactionId="TXN-123", region="NCR", ...),
        Ticket(transactionId="TXN-123", region="NCR", ...),
    ]
    clusters = await clustering_service.detect_clusters(tickets)
    assert len(clusters) == 1
    assert clusters[0].ticketCount == 2
    assert clusters[0].confidence == "High"
```

### 3. Run Tests (Red)

```bash
pytest tests/unit/test_clustering_service.py
# Should FAIL initially
```

### 4. Implement Feature (Green)

```python
# src/deduptickets/services/clustering_service.py
async def detect_clusters(tickets: list[Ticket]) -> list[Cluster]:
    # Implementation...
```

### 5. Run Tests Again

```bash
pytest tests/unit/test_clustering_service.py
# Should PASS now
```

### 6. Refactor & Lint

```bash
ruff check --fix .
ruff format .
mypy src/
```

### 7. Commit & Push

```bash
git add .
git commit -m "feat: add transaction ID clustering"
git push origin feature/your-feature-name
```

## Common Tasks

### Initialize Cosmos DB Containers

```bash
cd backend
python -m src.deduptickets.cosmos.setup

# This creates:
# - tickets container (pk: /pk)
# - clusters container (pk: /pk)
# - merges container (pk: /pk)
# - audit container (pk: /pk, TTL: 90 days)
# - spikes container (pk: /pk)
# - baselines container (pk: /pk)
```

### View Audit Logs

```bash
curl "http://localhost:8000/api/v1/audit?actionType=Merge" \
  -H "X-API-Key: your-api-key-here"
```

### Trigger Manual Clustering

```bash
# Clustering runs automatically every 5 minutes
# To trigger manually (dev only):
curl -X POST http://localhost:8000/api/v1/admin/trigger-clustering \
  -H "X-API-Key: your-api-key-here"
```

### Query Cosmos DB Directly

```python
# Python async client example
from azure.cosmos.aio import CosmosClient

async with CosmosClient(endpoint, key) as client:
    database = client.get_database_client("deduptickets-db")
    container = database.get_container_client("tickets")
    
    # Point read (1 RU)
    item = await container.read_item(item="ticket-id", partition_key="NCR|2025-12")
    
    # Query with partition key
    query = "SELECT * FROM c WHERE c.status = 'Open'"
    items = container.query_items(query, partition_key="NCR|2025-12")
    async for item in items:
        print(item)
```

## Troubleshooting

### Cosmos DB Emulator Connection Issues

```bash
# Check if emulator is running (Windows)
Get-Process *cosmos* -ErrorAction SilentlyContinue

# Check emulator health (Docker)
docker logs cosmosdb-emulator

# Download and trust SSL certificate
curl -k https://localhost:8081/_explorer/emulator.pem -o ~/cosmosdb-emulator.pem

# Disable SSL verification (development only)
# Set COSMOS_VERIFY_SSL=false in .env
```

### "Container does not exist" Errors

```bash
# Re-run container setup
cd backend
python -m src.deduptickets.cosmos.setup
```

### API Returns 401

Ensure `X-API-Key` header matches the `API_KEY` environment variable.

### Clustering Not Finding Duplicates

- Check tickets have matching fields (transactionId, merchant, etc.)
- Verify text similarity threshold (default 0.7) isn't too high
- Check logs: `docker compose logs backend | grep clustering`

### High RU Consumption

- Enable diagnostics logging: `LOG_LEVEL=DEBUG`
- Review query patterns - ensure partition key is used
- Check for cross-partition queries in logs
- Consider composite indexes for frequent query patterns

### Emulator Out of Memory

```bash
# Restart emulator with more partitions
docker stop cosmosdb-emulator
docker rm cosmosdb-emulator
docker run -d \
  --name cosmosdb-emulator \
  -e AZURE_COSMOS_EMULATOR_PARTITION_COUNT=5 \
  -m 3g \
  ...  # (rest of flags)
```

## Azure Deployment Notes

When deploying to Azure Cosmos DB:

1. Create Azure Cosmos DB account (NoSQL API)
2. Enable Hierarchical Partition Keys if using sub-partition patterns
3. Update environment variables with Azure connection string
4. Set `COSMOS_VERIFY_SSL=true` for production
5. Configure preferred regions for multi-region writes
6. Set up serverless or provisioned throughput based on workload

```bash
# Production environment variables
COSMOS_ENDPOINT=https://your-account.documents.azure.com:443
COSMOS_KEY=your-primary-key
COSMOS_DATABASE=deduptickets-db
COSMOS_VERIFY_SSL=true
```

## Next Steps

1. Review [spec.md](spec.md) for full feature requirements
2. Read [data-model.md](data-model.md) for container and document schemas
3. Explore [contracts/openapi.yaml](contracts/openapi.yaml) for API reference
4. Check [research.md](research.md) for technical decisions
