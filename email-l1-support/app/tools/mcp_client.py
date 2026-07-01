"""MCP (Model Context Protocol) client.

Launches the local MCP server (``mcp_server/kb_server.py``) over stdio, calls a
tool, and returns the result. If MCP is disabled in config or the ``mcp``
package is unavailable, ``call_tool`` returns ``None`` and the caller proceeds
without it.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


def call_tool(tool_name: str, arguments: dict[str, Any]) -> str | None:
    """Call an MCP tool from synchronous code.

    Handles being called both outside and inside a running event loop, since
    the FastAPI routes run in one.
    """
    if not settings.get("mcp", "enabled", default=False):
        return None
    try:
        return _run_sync(_call_tool_async(tool_name, arguments))
    except Exception as exc:
        logger.warning("MCP call failed (%s); continuing without it: %s", tool_name, exc)
        return None


def _run_sync(coro):
    """Run a coroutine to completion from sync code, even inside a live loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # A loop is already running: run in a worker thread with its own loop.
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(coro)).result()


async def _call_tool_async(tool_name: str, arguments: dict[str, Any]) -> str | None:
    # Imported lazily so a missing 'mcp' package does not break startup.
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    server_script = settings.resolve_path(
        settings.get("mcp", "server_script", default="mcp_server/kb_server.py")
    )
    params = StdioServerParameters(command=sys.executable, args=[str(server_script)])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)
            parts = []
            for block in result.content:
                text = getattr(block, "text", None)
                if text:
                    parts.append(text)
            return "\n".join(parts) if parts else None
