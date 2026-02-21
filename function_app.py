"""Azure Functions v2 entrypoint for ASGI-hosted FastAPI app."""

from __future__ import annotations

import sys
from pathlib import Path

import azure.functions as func

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"

if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from main import app as fastapi_app  # noqa: E402

app = func.AsgiFunctionApp(app=fastapi_app, http_auth_level=func.AuthLevel.ANONYMOUS)
