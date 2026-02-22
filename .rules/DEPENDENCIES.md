# Dependency Management

## Rules

1. **ALWAYS** update both `requirements.txt` AND `pyproject.toml` simultaneously — they must stay in sync
2. **ALWAYS** use exact versions with `==` in BOTH files (e.g., `azure-storage-blob==12.24.0`)
3. **NEVER** use `>=` or other version ranges — pin exact versions for reproducibility
4. **ALWAYS** check the latest library version with tools before installation — do not rely on past knowledge
5. Maintain alphabetical order within each section

## Version Checking Workflow

Before adding or updating any dependency:

```bash
# Use pip index to check latest version
pip index versions <package-name>

# Or use uv (faster alternative)
uv pip search <package-name>
```

## Example

Both files must use identical version specifications:

```toml
# pyproject.toml
dependencies = [
    "aiohttp==3.11.10",
    "azure-cosmos==4.14.1",
    "azure-functions==1.24.0",
    "azure-identity==1.25.1",
    "azure-storage-blob==12.24.0",
    "openai==2.7.1",
    "python-dotenv==1.2.1",
]
```

```
# requirements.txt
aiohttp==3.11.10
azure-cosmos==4.14.1
azure-functions==1.24.0
azure-identity==1.25.1
azure-storage-blob==12.24.0
openai==2.7.1
python-dotenv==1.2.1
```
