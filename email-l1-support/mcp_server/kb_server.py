"""MCP server exposing an internal ticket status lookup over stdio.

Maps a triaged category to any known open incident. Replace
``_KNOWN_INCIDENTS`` with a real CMDB / ServiceNow / Jira query as needed.

    python mcp_server/kb_server.py
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("internal-ticketing")


_KNOWN_INCIDENTS = {
    "database": "INC-1042 OPEN: DB connection pool exhaustion under investigation.",
    "network": "INC-2087 MONITORING: intermittent latency on the east gateway.",
    "authentication": "No active incident. SSO provider reporting healthy.",
}


@mcp.tool()
def lookup_ticket_status(subject: str, category: str) -> str:
    """Return any known open incident for the given category."""
    status = _KNOWN_INCIDENTS.get(
        (category or "").lower(),
        "No related open incident found for this category.",
    )
    return f"Ticket lookup for '{subject}' [{category}]: {status}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
