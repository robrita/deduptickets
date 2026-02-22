# Async & Parallel Execution Standards

## Core Rules

1. **Use `aiohttp`** instead of `requests` for HTTP calls — true async I/O without blocking the event loop
2. **Use `asyncio.gather()`** instead of `ThreadPoolExecutor` — true parallel I/O, lower overhead, better error handling
3. **Declare `async def`** for all route handlers and helper functions that perform I/O
4. **Use proper type guards** when processing `asyncio.gather()` results with `return_exceptions=True`

## Pattern: Async HTTP Requests

```python
import aiohttp
import asyncio

async def _execute_api_call(url: str, payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Make async HTTP request."""
    async with (
        aiohttp.ClientSession() as session,
        session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response,
    ):
        response.raise_for_status()
        result = await response.json()
        return (url, result)
```

## Pattern: Parallel Execution with Gather

```python
@app.route(route="batch_operation", methods=["POST"])
@require_api_key
async def batch_operation(req: func.HttpRequest) -> func.HttpResponse:
    tasks = [_execute_operation(item) for item in items]

    # Execute all tasks in parallel with exception handling
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results with proper type guards
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Operation failed: {str(result)}")
            continue

        if isinstance(result, tuple) and len(result) == 2:
            key, value = result
```

## Why These Patterns

| Approach | Benefit |
|----------|---------|
| `aiohttp` over `requests` | Non-blocking I/O, native async/await |
| `asyncio.gather()` over `ThreadPoolExecutor` | No GIL blocking, lower memory overhead |
| `async def` handlers | End-to-end non-blocking pipeline |
| Type guards on results | Safe handling of mixed success/exception results |
