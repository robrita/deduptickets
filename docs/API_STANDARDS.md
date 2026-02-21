# API Response Standards

## Success Response Structure

Every successful response must include:

```python
{
    # Core response data (varies by endpoint)
    "results": [...],           # For query/search endpoints
    "document": {...},          # For upsert endpoints

    # Standard metadata fields (REQUIRED)
    "request_id": "abc123",     # 8-character UUID for request tracking
    "performance": {
        "operation_ms": 123.45,  # Main operation time
        "total_ms": 150.67       # Total request processing time
    },

    # Additional context fields (as needed)
    "count": 10,
    "message": "Operation successful"
}
```

## Error Response Structure

```python
{
    "error": "Error Category",           # Brief error type
    "message": "Detailed explanation",   # Clear, actionable error message
    "request_id": "abc123"              # Include when available
}
```

## HTTP Status Codes

| Code | Usage |
|------|-------|
| `200` | Successful operation |
| `400` | Validation errors, missing required fields |
| `401` | Missing authentication |
| `403` | Invalid authentication credentials |
| `500` | Server-side errors, exceptions |

## Implementation Pattern

```python
@app.route(route="example", methods=["POST"])
@require_api_key
async def example_route(req: func.HttpRequest) -> func.HttpResponse:
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    logger.info(f"[{request_id}] Operation initiated")

    try:
        operation_start = time.time()
        result = await perform_operation()
        operation_time = time.time() - operation_start
        total_time = time.time() - start_time

        return func.HttpResponse(
            body=json.dumps({
                "result": result,
                "request_id": request_id,
                "performance": {
                    "operation_ms": round(operation_time * 1000, 2),
                    "total_ms": round(total_time * 1000, 2),
                }
            }),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as e:
        logger.error(f"[{request_id}] Operation failed: {str(e)}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({
                "error": "Operation failed",
                "message": str(e),
                "request_id": request_id
            }),
            mimetype="application/json",
            status_code=500,
        )
```

## Rules

1. **Always include `request_id`** — generate with `str(uuid.uuid4())[:8]` at handler start
2. **Always include `performance` metrics** — track timing with `time.time()`
3. **Consistent field names** — follow existing patterns (`result_count`, `total_results`)
4. **Actionable error messages** — tell users what went wrong and how to fix it
5. **Log all errors with context** — include request_id, operation type, error details
