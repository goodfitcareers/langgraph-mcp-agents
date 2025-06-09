from __future__ import annotations
from typing import Any
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "CitationTracker",
    instructions="Track citations in PostgreSQL",
    host="0.0.0.0",
    port=8013,
)

@mcp.tool()
async def track_extraction(source_document: str, extracted_fact: str, location: str) -> str:
    """Return a mock citation ID."""
    return "citation-1"


if __name__ == "__main__":
    mcp.run("stdio")
