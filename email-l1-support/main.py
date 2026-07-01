"""Application entry point. Starts the REST API server."""
from __future__ import annotations

import uvicorn

from app.config import settings
from app.server import create_app

app = create_app()


def _run() -> None:
    uvicorn.run(
        "main:app",
        host=settings.get("server", "host", default="127.0.0.1"),
        port=int(settings.get("server", "port", default=8080)),
        reload=False,
    )


if __name__ == "__main__":
    _run()
