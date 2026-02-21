# Quality Gates

## Mandatory Gates

After any meaningful backend change, complete **all** gates before considering work done:

1. **Lint & format** — `make lint` and `make format-check` (apply fixes with `make lint-fix` / `make format`)
2. **Security scan** — `make security` (Bandit)
3. **Type checking** — `make typecheck` (mypy)
4. **Tests** — `make test` (unit → contract → integration)
5. **Coverage** — meet or exceed 80% target (`make test-cov`)

## Ruff Error Resolution

After every code change:

1. Check for Ruff errors immediately after implementation
2. Fix all errors before considering the task complete
3. **NEVER** use `# type: ignore` or `# pyright: ignore` to suppress errors — fix the root cause
4. Only suppress in extremely rare confirmed false-positive cases

## Pre-commit & Secret Scanning

1. Install and use pre-commit hooks for formatting, linting, and file hygiene
2. Enable secret detection hooks (private key, credential checks)
3. Never commit credentials, keys, or connection strings to tracked files
4. Treat failed pre-commit checks as blockers — fix root causes

## Custom Lint Error Messages

When writing custom Ruff rules or lint scripts, encode **remediation instructions directly in the error message** so agents get fix guidance in-context automatically. Example:

```python
# ❌ Bad error message
"Import violation detected"

# ✅ Good error message with remediation
"Import violation: Service layer cannot import from Routes. "
"Move the shared logic to a utility in backend/src/lib/ and import from there."
```

This pattern turns lint errors into agent-actionable instructions without requiring documentation lookup.

## Frontend Mandatory Gates

After any meaningful frontend change, complete **all** gates before considering work done:

1. **Lint** — `make frontend-lint` (ESLint)
2. **Format check** — `make frontend-format-check` (Prettier)
3. **Type check & Build** — `make frontend-build` (runs `tsc && vite build`)
4. **Unit tests** — `make frontend-test` (Vitest)
5. **E2E tests** — `make frontend-test-e2e` (Playwright, when applicable)

Quick combined check: `make frontend-ci`

### Frontend Theme Rules

See [docs/FRONTEND_THEME.md](FRONTEND_THEME.md) for the full guide. Key enforcement points:

- **No hardcoded `blue-*` or `indigo-*`** for brand/interactive colors — use `primary-*` tokens.
- **Use component classes** (`.btn-primary`, `.card`, etc.) before writing custom Tailwind utilities.
- **Import from `theme/colors.ts`** for status/priority/severity badges — never duplicate inline maps.

## Common Scenarios & Solutions

### Azure Functions Request Headers

```python
# ❌ PROBLEM: Type inference fails
cosmos_endpoint = req.headers.get("X-Cosmos-Endpoint")  # Type: Unknown | None

# ✅ SOLUTION: Cast headers to dict[str, str]
from typing import cast
headers = cast(dict[str, str], req.headers)
cosmos_endpoint = headers.get("X-Cosmos-Endpoint")  # Type: str | None
```

### Content-Length Header

```python
# ❌ PROBLEM: int() receives unknown type
content_length = int(req.headers.get("Content-Length", 0))

# ✅ SOLUTION: Cast headers and use string default
headers = cast(dict[str, str], req.headers)
content_length = int(headers.get("Content-Length", "0"))
```

### Exception Headers with Partially Unknown Types

```python
# ❌ PROBLEM: Exception headers are partially unknown
retry_after = float(e.headers.get("x-ms-retry-after-ms", 1000)) / 1000.0

# ✅ SOLUTION: Use getattr() to safely access the attribute
headers_attr: Any = getattr(e, "headers", {})
error_headers = cast(dict[str, Any], headers_attr)
retry_after = float(error_headers.get("x-ms-retry-after-ms", 1000)) / 1000.0
```

**Principle**: For SDK objects with partially unknown attributes, use `getattr()` to extract into `Any`, then `cast()` to the desired type.

### Dictionary Initialization

```python
# ❌ PROBLEM: Ruff infers dict[str, Unknown]
health_status = {"status": "healthy", "timestamp": time.time(), "checks": {}}

# ✅ SOLUTION: Add explicit type annotation
health_status: dict[str, Any] = {"status": "healthy", "timestamp": time.time(), "checks": {}}
```

### Extracting Headers + Initializing Clients

When multiple handlers need headers + client init, merge into one function:

```python
# ✅ Single function returns container or error response
def get_cosmos_container(req: func.HttpRequest, request_id: str) -> Any | func.HttpResponse:
    headers = cast(dict[str, str], req.headers)
    endpoint = headers.get("X-Cosmos-Endpoint")
    # ... validation, client initialization
    # Return container or error response directly
```
