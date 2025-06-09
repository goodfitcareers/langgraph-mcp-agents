from __future__ import annotations
import os
import logging
from typing import Any, Dict

import PyPDF2
from docx import Document

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "DocumentProcessor",
    instructions="Parse PDF, DOCX, and TXT resumes",
    host="0.0.0.0",
    port=8011,
)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}


def _read_pdf(path: str) -> str:
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        return "\n".join(page.extract_text() or "" for page in reader.pages)


def _read_docx(path: str) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def _read_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@mcp.tool()
async def extract_text(document_path: str) -> str:
    """Extract text from a supported document."""
    ext = os.path.splitext(document_path)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")
    if ext == ".pdf":
        return _read_pdf(document_path)
    if ext in {".docx", ".doc"}:
        return _read_docx(document_path)
    return _read_txt(document_path)


@mcp.tool()
async def process_resume(document_path: str) -> Dict[str, Any]:
    """Stub extraction using Claude Sonnet 4"""
    text = await extract_text(document_path)
    # Placeholder for Claude integration
    return {"text": text, "roles": []}


if __name__ == "__main__":
    mcp.run("stdio")
