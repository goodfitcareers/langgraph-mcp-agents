import sys
import pathlib
import asyncio
import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
from mcp_servers.document_processor import server as dp

@pytest.mark.asyncio
async def test_extract_text_txt(tmp_path):
    file = tmp_path / "sample.txt"
    file.write_text("hello")
    text = await dp.extract_text(str(file))
    assert text.strip() == "hello"
