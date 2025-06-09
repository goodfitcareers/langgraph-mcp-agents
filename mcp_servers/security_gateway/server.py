from __future__ import annotations
import logging
import re
from typing import Any, Dict
from mcp.server.fastmcp import FastMCP
from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "SecurityGateway",
    instructions="Validate and forward requests to other MCP servers",
    host="0.0.0.0",
    port=8010,
)

RATE_LIMIT = 5  # simplistic per-process limit
request_count = 0

SAFE_PATH = re.compile(r"^[\w\-/\\.]+$")


def _validate_params(params: Dict[str, Any]) -> bool:
    if request_count > RATE_LIMIT:
        raise RuntimeError("Rate limit exceeded")
    for value in params.values():
        if isinstance(value, str) and not SAFE_PATH.match(value):
            raise ValueError("Invalid characters in input")
    return True


@mcp.tool()
async def validate_and_forward(target_server: str, method: str, params: Dict[str, Any]) -> Any:
    """Validate input and forward to target MCP server."""
    global request_count
    _validate_params(params)
    request_count += 1
    client = MultiServerMCPClient.from_file("mcp-config.yaml")
    response = await client.acall(target_server, method, **params)
    return response


if __name__ == "__main__":
    mcp.run("stdio")
