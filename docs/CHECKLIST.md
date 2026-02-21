# Implementation Checklist

Before marking any task as complete, verify every applicable item:

## Code Quality

- [ ] Code is Azure Functions serverless-compatible (no file system writes, all in-memory)
- [ ] All Ruff errors are resolved
- [ ] Lint/format, security scan, and type checking passed
- [ ] No code duplication (check for reusable patterns)
- [ ] Error handling is implemented
- [ ] Logging is added for debugging
- [ ] Logging is sanitized (no secrets, keys, or sensitive payloads)
- [ ] Security best practices followed (input validation, OWASP)
- [ ] Cross-platform compatibility (Windows/Linux) preserved

## API Standards

- [ ] Response follows standardized format with `request_id` and `performance` fields
- [ ] Appropriate HTTP status codes used
- [ ] Error responses include actionable messages
- [ ] External calls have explicit timeouts and retry handling

## Async & I/O

- [ ] Use `aiohttp` for HTTP requests, not `requests`
- [ ] Use `asyncio.gather()` for parallel execution, not `ThreadPoolExecutor`
- [ ] Route handlers and I/O functions declared as `async def`

## Dependencies

- [ ] Both `requirements.txt` and `pyproject.toml` updated and in sync (if changed)

## Documentation & Testing

- [ ] Test cases added to `test.http` for new routes or endpoints
- [ ] Multiple test scenarios included: happy path, edge cases, error cases, input variations
- [ ] Descriptive comments added for each test case
- [ ] `README.md` updated with endpoint documentation (if new/changed routes)
- [ ] Endpoint path, method, parameters, headers, body format, and response structure documented
- [ ] curl examples added in Testing section for new endpoints

## Frontend

- [ ] No hardcoded `blue-*` or `indigo-*` classes for brand colors — use `primary-*` tokens
- [ ] Component classes used where available (`.btn-primary`, `.card`, `.badge-*`, etc.)
- [ ] Status/priority/severity maps imported from `theme/colors.ts` (not duplicated inline)
- [ ] ESLint passes (`make frontend-lint`)
- [ ] Prettier passes (`make frontend-format-check`)
- [ ] TypeScript compiles and Vite build succeeds (`make frontend-build`)
- [ ] Unit tests pass (`make frontend-test`)
- [ ] No new Tailwind classes that duplicate existing component classes in `index.css`

## Agent Interaction

- [ ] New rules added to AGENTS.md follow the map pattern (one-liner + pointer to `docs/` topic file)
- [ ] Clarifying questions use plain text with numbered options (no checkbox/radio UI)
