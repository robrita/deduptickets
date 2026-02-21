# Serverless & Platform Compatibility

## Azure Functions Constraints

ALL code must be compatible with Azure Functions serverless environment.

### Rules

1. **NEVER write to the file system** except for `/tmp` (ephemeral)
2. **Process all data in-memory** using streams, buffers, and memory-based operations
3. **No persistent local state** — use Azure Storage, Cosmos DB, or other cloud services
4. **Stateless operations** — each function invocation must be independent
5. **Use streaming for large files** (e.g., `fitz.open(stream=bytes)` instead of file paths)
6. **Avoid file-based operations** like `open()`, `Path().write()`, `os.makedirs()`
7. **Return results via HTTP responses** or output bindings, never via local files

### Why

- Azure Functions file system is read-only (except `/tmp`)
- `/tmp` is limited in size and cleared between cold starts
- Serverless environments are ephemeral and scale horizontally
- File-based operations will fail in production

### Correct Patterns

```python
# ✅ CORRECT: Load from memory/stream
pdf_document = fitz.open(stream=image_bytes, filetype="pdf")
image = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)

# ❌ WRONG: File system operations
with open("temp.pdf", "wb") as f:  # Will fail in serverless
    f.write(pdf_data)
pdf_document = fitz.open("temp.pdf")
```

## Cross-Platform Compatibility

All code and scripts must work on both Windows and Linux:

1. Use `pathlib.Path` (or equivalent cross-platform APIs) for file/path operations
2. Avoid shell-specific assumptions in scripts and commands
3. Keep line endings and path separators platform-agnostic
4. Validate that local development commands are reproducible across environments
