# Code Patterns & Reusability

## Before Implementing Anything

1. Check if similar logic exists elsewhere in the codebase
2. Create reusable helper functions instead of duplicating code across routes
3. Extract common patterns into shared utilities
4. When two functions are always called together, consider merging them

## Validation Helper Functions

The following helpers are available for common API request validation:

### `_validate_env_variables(required_vars, request_id)`

Validates required environment variables are set. Returns `HttpResponse` error or `None`.

```python
env_error = _validate_env_variables(
    {"AZURE_OPENAI_API_KEY": AZURE_OPENAI_API_KEY, "AZURE_OPENAI_ENDPOINT": AZURE_OPENAI_ENDPOINT},
    request_id,
)
if env_error:
    return env_error
```

### `_validate_padding_parameter(padding_str, request_id)`

Validates and parses padding parameter (0–50% range). Returns `(value, error_response)`.

```python
padding, padding_error = _validate_padding_parameter(padding_str, request_id)
if padding_error:
    return padding_error
```

### `_parse_json_body(req, request_id)`

Parses and validates JSON request body. Returns `(body_dict, error_response)`.

```python
body, body_error = _parse_json_body(req, request_id)
if body_error:
    return body_error
```

### `_validate_required_fields(body, required_fields, request_id)`

Validates required fields are present. Returns `HttpResponse` error or `None`.

```python
fields_error = _validate_required_fields(body, ["filename", "content"], request_id)
if fields_error:
    return fields_error
```

### `_decode_base64_content(base64_content, request_id)`

Decodes base64 content. Returns `(decoded_bytes, error_response)`.

```python
image_bytes, decode_error = _decode_base64_content(base64_content, request_id)
if decode_error:
    return decode_error
```

### Error-Handling Convention

All helpers follow a consistent pattern:
- **Tuple return**: `(result, None)` on success, `(default, HttpResponse)` on failure
- **Validation-only**: returns `HttpResponse` on failure, `None` on success
- Always check errors immediately and return early if validation fails

## Feature Removal Workflow

When removing features or dependencies, follow this order:

1. **Dependencies** — remove from both `requirements.txt` AND `pyproject.toml`
2. **Imports** — remove all import statements
3. **Configuration** — remove setup code, constants, environment variables
4. **Helper functions** — remove utility functions specific to the feature
5. **Usage** — find all calls with grep/search and remove
6. **Documentation** — update config templates and comments
7. **Verify** — grep for zero remaining references
8. **Lint** — ensure no errors introduced

### Key Lessons

- Use grep/search extensively to find all occurrences before removal
- Remove in the order above (dependencies → imports → setup → helpers → usage → config)
- Verify each step to catch missed references
- Always preserve unrelated improvements when removing specific features
