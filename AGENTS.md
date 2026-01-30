
# Backend Development (Python/FastAPI)

## Code Quality Standards (Ruff)

### Formatting Rules

- **Line length**: 100 chars (enforced in `pyproject.toml`)
- **Quotes**: Double quotes only
- **Target**: Python 3.12+
- **Pre-commit**: Run `make format` before every commit
- **Cross-platform**: Ensure all code works on both Windows and Linux (use `pathlib.Path`, avoid shell-specific commands)

### Per-File Ignores

- `__init__.py`: Ignores `F401` (unused imports are acceptable for package exports)

### Ruff Rules Enabled

`E`, `W`, `F`, `I`, `B`, `C4`, `UP`, `ARG`, `SIM`, `TCH`, `PTH`, `PL`, `RUF`, `S`, `ASYNC`

### Development Commands (run from `backend/`)

```bash
make dev            # Start FastAPI dev server with hot reload
make lint           # Check code style (non-destructive)
make lint-fix       # Auto-fix lint issues
make format         # Auto-fix + format (idempotent, safe to run repeatedly)
make format-check   # Check formatting without modifying
make security       # Run Bandit security scan (B101 skipped for asserts)
make typecheck      # Run type checking
make ci             # Full pipeline: lint + format-check + security + typecheck + test-cov
```

### Best Practices

1. Always run `make format` before committing
2. Fix lint errors before running the app
3. Keep code idiomatic to Python 3.12+ (use type hints, modern syntax)
4. Maintain consistency with existing codebase patterns

### Pydantic Settings Pattern

- Use `SecretStr` for sensitive values (`cosmos_key`, `api_key`)
- Use `@lru_cache` for singleton settings instance
- Define field validators with `ge`/`le` constraints
- Use `Literal` for enum-like values

### Architecture Patterns

- **Repository Pattern**: Base class in `repositories/base.py` for Cosmos DB operations with generic types
- **Service Layer**: Business logic in `services/` (ClusteringService, MergeService, etc.)
- **Dependency Injection**: FastAPI's `Depends` pattern throughout routes
- **Async-first**: All database operations use `async`/`await`

---

# Documentation notes

- Do not create a new markdown file for summary documentation on new features.
- Write the concise documentation by updating the README.md file instead.

---

# Frontend Development (React/TypeScript/Vite)

## Quick Commands (run from `frontend/`)

```bash
npm run dev          # Start Vite dev server (port 3000)
npm run build        # TypeScript check + Vite production build
npm run preview      # Preview production build locally
npm run lint         # ESLint with max 0 warnings
npm run lint:fix     # Auto-fix ESLint issues
npm run format       # Prettier format all src files
npm run format:check # Check formatting without modifying
npm run test         # Run Vitest unit tests
npm run test:e2e     # Run Playwright E2E tests
```

## Code Style

- **Quotes**: Single quotes only
- **Semicolons**: Required
- **Line width**: 100 characters
- **Trailing comma**: ES5 style
- **Arrow parens**: Omit when single parameter

## TypeScript

- Strict mode enabled
- Use path alias `@/` for src imports
- Define prop interfaces with `Props` suffix
- Types centralized in `src/types/index.ts`

## Component Patterns

- Functional components with named + default exports
- JSDoc comment at file top
- Props interface defined before component
- Use Tailwind utility classes for styling

```tsx
/**
 * ComponentName description.
 */
export interface ComponentNameProps {
  requiredProp: string;
  optionalProp?: number;
  onAction?: (id: string) => void;
}

export function ComponentName({ requiredProp, optionalProp, onAction }: ComponentNameProps) {
  return <div>...</div>;
}

export default ComponentName;
```

## Hooks Patterns

- Return object with named properties
- Include `isLoading` and `error` states
- Use `useCallback` for stable function references

## Service Layer

- Use `api.get/post/put/delete` from `@/services/api`
- Export individual functions + namespace object
- Always type return values with `Promise<T>`

## Environment Variables

- Prefix with `VITE_` (e.g., `VITE_API_URL`)
- Document in `.env.example`

---

# Testing Guidelines

## Backend (pytest)

```bash
make test-unit        # Run unit tests only
make test-contract    # Run API contract tests
make test-integration # Run integration tests
make test-cov         # Run all tests with coverage report
```

- **Coverage minimum**: 80% (`--cov-fail-under=80`)
- **Markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.contract`, `@pytest.mark.slow`
- **Fixtures**: Use `conftest.py` fixtures (`mock_container`, `ticket_factory`, `auth_headers`)
- **Async tests**: Use `pytest-asyncio` with `async def test_...`

## Frontend (Vitest + Playwright)

```bash
npm run test         # Vitest unit tests
npm run test:e2e     # Playwright E2E tests
```

---

# Pre-commit Hooks

Install hooks once after cloning:

```bash
cd backend && make pre-commit-install
```

Key hooks:
- `trailing-whitespace`, `end-of-file-fixer` — file hygiene
- `check-yaml/json/toml` — config file validation
- `check-added-large-files` — block files > 1000KB
- `no-commit-to-branch` — block direct commits to `main`
- `detect-private-key` — prevent credential commits
- `ruff`, `ruff-format` — Python lint + format
- `bandit` — Python security scan
- `eslint`, `prettier` — Frontend lint + format

---

# Docker Local Development

```bash
make docker-up    # Start all services (Cosmos emulator, backend, frontend)
make docker-down  # Stop all services
make docker-logs  # View logs
make docker-build # Rebuild images
```

**Cosmos DB Emulator**: Runs on port 8081 with test credentials. Set `COSMOS_SSL_VERIFY=false` for local dev.

---

# API Contract Alignment

Frontend types in `frontend/src/types/index.ts` must match the OpenAPI spec at `specs/001-ticket-dedup-dashboard/contracts/openapi.yaml`.

When updating API contracts:
1. Update `openapi.yaml` first
2. Update backend Pydantic schemas
3. Update frontend TypeScript types
4. Run contract tests: `make test-contract`

---

# Import Ordering

## Python (Ruff `I` rule - isort)

Enforced automatically. Order:
1. Standard library
2. Third-party packages
3. Local imports

## TypeScript

Recommended order (not auto-enforced):
1. React imports
2. External libraries
3. `@/` path aliases
4. Relative imports

---

# Git Operations Requiring Explicit Approval

**CRITICAL**: The following Git operations must NEVER be performed without explicit human approval:

- `git branch -d` / `git branch -D` (delete local branch)
- `git push origin --delete` (delete remote branch)
- `git reset --hard` (discard commits)
- `git push --force` / `git push -f` (force push)
- `git rebase` on shared branches

Even after a successful merge, always ask before deleting feature branches.

---

# Dependency Management

- Add packages via `uv add <package>` (updates `pyproject.toml` and `uv.lock`)
- Remove packages via `uv remove <package>`
- After adding/removing, run `uv sync` to update environment
- Pin versions for production stability when needed

---

# Environment Variables

## General Rules

- Document all new env vars in `.env.example` with placeholder values
- Never commit actual credentials to `.env` (gitignored)
- Use descriptive names with service prefix
- Group related vars with comments in `.env.example`

## Backend Variables

| Variable | Description |
|----------|-------------|
| `COSMOS_ENDPOINT` | Azure Cosmos DB endpoint |
| `COSMOS_KEY` | Cosmos DB key (use emulator key for dev) |
| `COSMOS_DATABASE` | Database name |
| `COSMOS_SSL_VERIFY` | SSL verification (`false` for emulator) |
| `API_KEY` | API authentication key |
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `SIMILARITY_THRESHOLD` | Text matching threshold (0.0-1.0) |

## Frontend Variables

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Backend API URL |

---

# Breaking Changes

When making breaking changes to APIs or data schemas:

- Bump version in `pyproject.toml` if applicable
- Document migration steps in commit message or PR description
- Update affected tests before merging
- Notify team members if shared interfaces change

---

# Quality Gate Checklist (Before Merge)

**MANDATORY**: Complete these steps after ANY feature change or update, and before merging. All gates must pass.

## Backend Quality Gates (run from `backend/`)

1. **Lint & Format**
   ```bash
   make format         # Auto-fix + format (run first)
   make lint           # Verify no lint errors remain
   ```
   - [ ] `make format` produces no changes (code already formatted)
   - [ ] `make lint` passes with zero errors

2. **Security Scan**
   ```bash
   make security       # Bandit security scan
   ```
   - [ ] No security warnings (B101 skipped for asserts)

3. **Type Checking**
   ```bash
   make typecheck      # mypy/pyright static analysis
   ```
   - [ ] Type errors resolved

4. **Unit Tests**
   ```bash
   make test-unit      # Run unit tests only
   make test-cov       # Full tests with coverage report
   ```
   - [ ] All unit tests pass
   - [ ] Coverage ≥80% (`--cov-fail-under=80`)

5. **Contract & Integration Tests** (requires Cosmos Emulator)
   ```bash
   make test-contract      # API contract tests
   make test-integration   # Integration tests
   ```
   - [ ] Contract tests pass (API matches OpenAPI spec)
   - [ ] Integration tests pass

## Frontend Quality Gates (run from `frontend/`)

1. **Lint & Format**
   ```bash
   npm run lint:fix    # Auto-fix ESLint issues
   npm run format      # Prettier format
   npm run lint        # Verify no warnings (max 0)
   npm run format:check # Verify formatting
   ```
   - [ ] `npm run lint` passes with zero warnings
   - [ ] `npm run format:check` shows no changes needed

2. **Type Check & Build**
   ```bash
   npm run build       # TypeScript check + Vite production build
   ```
   - [ ] Build completes without TypeScript errors

3. **Unit Tests**
   ```bash
   npm run test        # Vitest unit tests
   ```
   - [ ] All unit tests pass

4. **E2E Tests** (requires backend running)
   ```bash
   npm run test:e2e    # Playwright E2E tests
   ```
   - [ ] E2E tests pass

## Combined CI Pipeline

Run the full backend pipeline with a single command:
```bash
cd backend && make ci   # lint + format-check + security + typecheck + test-cov
```

## General Requirements

1. **Documentation**
   - [ ] README.md updated if user-facing changes
   - [ ] Docstrings added for new public functions

2. **Git Hygiene**
   - [ ] Commit messages follow conventional format (`feat:`, `fix:`, `docs:`)
   - [ ] No secrets/credentials committed

3. **Review**
   - [ ] Self-review of diff before commit
   - [ ] Run app locally to verify functionality

## Quick Validation Commands

Full validation before any feature merge:

```bash
# Backend (from backend/)
make ci

# Frontend (from frontend/)
npm run lint && npm run format:check && npm run build && npm run test
```

---

# Observability

- Use module-level loggers (`logger = logging.getLogger(__name__)`)
- Log key actions and outcomes (data loads, API calls, errors)
- Prefer built-in generics (`list`, `dict`) over `typing.List`/`typing.Dict`
