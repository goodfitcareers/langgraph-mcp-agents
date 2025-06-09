from __future__ import annotations
from typing import Any, Dict, List
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "NotionIntegration",
    instructions="Manage professional history in Notion",
    host="0.0.0.0",
    port=8012,
)

# Stubs for demonstration

@mcp.tool()
async def query_existing_roles(client_id: str) -> List[Dict[str, Any]]:
    """Return mock roles for a client."""
    return []


@mcp.tool()
async def update_role_information(role_id: str, updates: Dict[str, Any], citations: List[Dict[str, Any]]) -> bool:
    """Update a role with citations."""
    return True


if __name__ == "__main__":
    mcp.run("stdio")
