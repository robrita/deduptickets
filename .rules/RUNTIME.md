# Runtime & Observability

Guidelines for function structure, timeouts, retry logic, client management, and logging.

## Running Azure Functions Runtime v4 (Local)

Use this runbook to start the local Function App host for this repository.

### Prerequisites

1. Azure Functions Core Tools v4 installed (`func --version` should return `4.x`)
2. Python environment activated (`.venv`)
3. Backend dependencies installed:

```bash
pip install -r requirements.txt
```

4. Frontend assets built (required for SPA hosting paths):

```bash
cd frontend
npm ci
npm run build
cd ..
```

5. Local settings available in `local.settings.json` with required app values.

### Keeping `.env` and `local.settings.json` in Sync

`.env` drives `uvicorn` (FastAPI dev server). `local.settings.json` drives `func start` (Azure Functions host).
Both must specify the **same** connection values for Cosmos DB, OpenAI, and auth — otherwise one entry point works and the other silently fails.

| Key | `.env` | `local.settings.json` `Values` | Notes |
|-----|--------|--------------------------------|-------|
| `COSMOS_ENDPOINT` | ✅ | ✅ | Must match |
| `COSMOS_USE_AAD` | ✅ | ✅ | Must match |
| `COSMOS_DATABASE` | ✅ | ✅ | Must match |
| `COSMOS_SSL_VERIFY` | ✅ | ✅ | `true` for cloud, `false` for emulator |
| `COSMOS_KEY` | optional | optional | Only when `COSMOS_USE_AAD=false` |
| `AZURE_TENANT_ID` | ✅ | ✅ | Required for AAD auth |
| `AZURE_OPENAI_ENDPOINT` | ✅ | ✅ | Must match |
| `AZURE_OPENAI_USE_AAD` | ✅ | ✅ | Must match |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | ✅ | ✅ | Must match |
| `API_KEY` | ✅ | ✅ | Must match |

**Rule:** When you update a connection value in `.env`, update `local.settings.json` in the same change (and vice versa).

### Start Host

```bash
func start --verbose
```

Expected success indicators:
- `Worker process started and initialized.`
- Function list includes `asgi_router`
- Host listens on `http://localhost:7071`

### Quick Smoke Tests

```bash
curl http://localhost:7071/health
curl http://localhost:7071/docs
curl http://localhost:7071/api/v1/clusters
```

### Common Runtime v4 Issues

1. **Missing assembly (`Microsoft.AspNetCore.Authentication.JwtBearer`)**
    - Symptom: host exits during startup before function indexing
    - Fix:

```powershell
$bundleRoot = Join-Path $HOME '.azure-functions-core-tools\Functions\ExtensionBundles\Microsoft.Azure.Functions.ExtensionBundle'
if (Test-Path $bundleRoot) { Remove-Item -Recurse -Force $bundleRoot }
func start --verbose
```

2. **MSI install lock (`winget` error 1618)**
    - Symptom: Core Tools upgrade/install blocked by another installer session
    - Fix: close pending installer sessions, then retry `winget install/upgrade` for Core Tools.

3. **Wrong Core Tools binary on PATH**
    - Symptom: unexpected `func` version or mixed behavior
    - Check:

```powershell
where.exe func
func --version
```

Use the binary that resolves to a working v4 runtime for local execution.

## Function Structure

Keep Azure Functions handlers thin — delegate to service/business logic layers.

```python
# ✅ CORRECT: Thin handler, logic in service layer
@app.route(route="tickets", methods=["GET"])
@require_api_key
async def get_tickets(req: func.HttpRequest) -> func.HttpResponse:
    request_id = str(uuid.uuid4())
    return await ticket_service.list_tickets(req, request_id)

# ❌ WRONG: Business logic inside the handler
@app.route(route="tickets", methods=["GET"])
@require_api_key
async def get_tickets(req: func.HttpRequest) -> func.HttpResponse:
    container = cosmos_client.get_container("tickets")
    query = "SELECT * FROM c WHERE c.status = 'open'"
    items = [item async for item in container.query_items(query)]
    # ... 50 more lines of logic ...
```

## Timeouts

Configure explicit timeouts for all external calls (Cosmos DB, Blob Storage, OpenAI, HTTP APIs).

```python
# ✅ CORRECT: Explicit timeout
async with aiohttp.ClientSession() as session:
    async with session.post(
        url, json=payload, timeout=aiohttp.ClientTimeout(total=30)
    ) as response:
        result = await response.json()

# ❌ WRONG: No timeout — can hang indefinitely
async with aiohttp.ClientSession() as session:
    async with session.post(url, json=payload) as response:
        result = await response.json()
```

## Retry Logic

Apply retry logic for transient failures: HTTP 429 (Request Rate Too Large), timeouts, and transient 5xx errors.

```python
# ✅ CORRECT: Retry with backoff for transient failures
MAX_RETRIES = 3
for attempt in range(MAX_RETRIES):
    try:
        result = await execute_request()
        break
    except CosmosHttpResponseError as e:
        if e.status_code == 429 and attempt < MAX_RETRIES - 1:
            retry_after = int(e.headers.get("x-ms-retry-after-ms", 1000)) / 1000
            await asyncio.sleep(retry_after)
            continue
        raise
```

## Client Reuse

Use singleton/module-level factories. Never create clients per request.

```python
# ✅ CORRECT: Module-level singleton
_cosmos_client: CosmosClient | None = None

def get_cosmos_client() -> CosmosClient:
    global _cosmos_client
    if _cosmos_client is None:
        _cosmos_client = CosmosClient(endpoint, credential)
    return _cosmos_client

# ❌ WRONG: New client per request — connection overhead, resource leaks
async def handle_request(req):
    client = CosmosClient(endpoint, credential)  # created every call
    container = client.get_container("tickets")
```

## Logging

Use module-level loggers. Include `request_id` and timing in log messages. Never log secrets, keys, or tokens.

```python
# ✅ CORRECT: Module-level logger with request context
logger = logging.getLogger(__name__)

async def process_tickets(request_id: str) -> None:
    start = time.perf_counter()
    logger.info("Processing tickets", extra={"request_id": request_id})
    # ... work ...
    elapsed = time.perf_counter() - start
    logger.info("Completed in %.2fs", elapsed, extra={"request_id": request_id})

# ❌ WRONG: Logging sensitive data
logger.info(f"Connecting with key={api_key}")  # NEVER log secrets
```

## Summary

| Rule | Rationale |
|------|-----------|
| Thin handlers | Separation of concerns; testability |
| Explicit timeouts | Prevent indefinite hangs in serverless |
| Retry with backoff | Resilience against transient failures |
| Singleton clients | Avoid connection overhead and resource leaks |
| Structured logging | Debuggability without exposing secrets |
