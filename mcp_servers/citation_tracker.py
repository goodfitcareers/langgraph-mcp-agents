import os
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, TypedDict

from dotenv import load_dotenv
from mcp.server import FastMCP, tool

# Attempt to import psycopg2
try:
    import psycopg2
    from psycopg2.extras import DictCursor
except ImportError:
    psycopg2 = None
    DictCursor = None
    print("CRITICAL: psycopg2 library not found. Citation tracking (PostgreSQL) will not be available.")

# Load environment variables
load_dotenv(override=True)

DATABASE_URL = os.getenv("DATABASE_URL")

# --- Type Definitions ---

class DocumentLocation(TypedDict, total=False):
    document_id: str # Hash of the document or unique ID
    page_number: Optional[int]
    paragraph_number: Optional[int]
    custom_location_info: Optional[str]

class Citation(TypedDict):
    citation_id: str # UUID
    source_document_fingerprint: str
    original_extracted_text: str
    document_location: DocumentLocation
    notion_page_id: Optional[str]
    notion_field_name: Optional[str]
    timestamp: str # ISO format datetime string

# --- Database Setup ---

def get_db_connection():
    """Establishes a new database connection."""
    if not psycopg2 or not DATABASE_URL:
        raise ConnectionError("psycopg2 library or DATABASE_URL not available.")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL database: {e}")
        raise ConnectionError(f"Database connection failed: {e}")


def init_citation_db():
    """Initializes the citations table in the PostgreSQL database if it doesn't exist."""
    if not psycopg2 or not DATABASE_URL:
        print("Cannot initialize database: psycopg2 library or DATABASE_URL not available.")
        return False

    table_creation_sql = """
    CREATE TABLE IF NOT EXISTS citations (
        citation_id UUID PRIMARY KEY,
        source_document_fingerprint TEXT NOT NULL,
        original_extracted_text TEXT NOT NULL,
        document_id TEXT,
        page_number INTEGER,
        paragraph_number INTEGER,
        custom_location_info TEXT,
        notion_page_id TEXT,
        notion_field_name TEXT,
        timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(table_creation_sql)
                conn.commit()
        print("Citations table initialized successfully (or already exists).")
        return True
    except ConnectionError: # Raised by get_db_connection if it fails
        print("Database connection failed during init_citation_db.")
        return False
    except psycopg2.Error as e:
        print(f"Error during database initialization: {e}")
        return False


# --- MCP Server Definition ---
mcp = FastMCP(
    name="CitationTracker",
    description="Manages citations and source attribution for extracted information.",
    instructions=(
        "Use this server to record where information was extracted from (source document, location) "
        "and where it was stored (e.g., Notion page/field). You can also retrieve these citations."
    )
)

# --- MCP Tools ---

@mcp.tool()
async def track_extraction(
    source_document_fingerprint: str,
    original_extracted_text: str,
    document_location: Dict[str, Any], # Should conform to DocumentLocation
    notion_page_id: Optional[str] = None,
    notion_field_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Records a citation for a piece of extracted text, linking it to its source and destination.
    """
    print(f"[CitationTracker] Received track_extraction request for doc fingerprint: {source_document_fingerprint}")
    if not psycopg2 or not DATABASE_URL:
        return {"error": "Database support not available.", "status": "failure"}

    citation_id = str(uuid.uuid4())
    timestamp_str = datetime.now(timezone.utc).isoformat()

    # Validate and structure document_location
    # For MVP, assume document_location dict is valid. Robust impl would validate keys.
    doc_loc_typed: DocumentLocation = {
        "document_id": document_location.get("document_id", ""), # Ensure required field
        "page_number": document_location.get("page_number"),
        "paragraph_number": document_location.get("paragraph_number"),
        "custom_location_info": document_location.get("custom_location_info"),
    }
    if not doc_loc_typed["document_id"]:
         return {"error": "document_location must contain a 'document_id'.", "status": "failure"}


    insert_sql = """
    INSERT INTO citations (
        citation_id, source_document_fingerprint, original_extracted_text,
        document_id, page_number, paragraph_number, custom_location_info,
        notion_page_id, notion_field_name, timestamp
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(insert_sql, (
                    citation_id,
                    source_document_fingerprint,
                    original_extracted_text,
                    doc_loc_typed.get("document_id"),
                    doc_loc_typed.get("page_number"),
                    doc_loc_typed.get("paragraph_number"),
                    doc_loc_typed.get("custom_location_info"),
                    notion_page_id,
                    notion_field_name,
                    timestamp_str
                ))
                conn.commit()
        print(f"[CitationTracker] Successfully tracked extraction with citation ID: {citation_id}")
        return {"citation_id": citation_id, "status": "success"}
    except ConnectionError as e:
        return {"error": f"Database connection error: {e}", "status": "failure"}
    except psycopg2.Error as e:
        error_msg = f"Database error tracking extraction: {e}"
        print(f"[CitationTracker] {error_msg}")
        return {"error": error_msg, "status": "failure"}
    except Exception as e:
        error_msg = f"Unexpected error tracking extraction: {e}"
        print(f"[CitationTracker] {error_msg}")
        return {"error": error_msg, "status": "failure"}


def _map_row_to_citation(row: Dict[str, Any]) -> Citation:
    """Helper to map a database row (from DictCursor) to a Citation TypedDict."""
    doc_loc: DocumentLocation = {
        "document_id": row["document_id"],
    }
    if row["page_number"] is not None:
        doc_loc["page_number"] = row["page_number"]
    if row["paragraph_number"] is not None:
        doc_loc["paragraph_number"] = row["paragraph_number"]
    if row["custom_location_info"] is not None:
        doc_loc["custom_location_info"] = row["custom_location_info"]

    return Citation(
        citation_id=str(row["citation_id"]), # Ensure UUID is string
        source_document_fingerprint=row["source_document_fingerprint"],
        original_extracted_text=row["original_extracted_text"],
        document_location=doc_loc,
        notion_page_id=row["notion_page_id"],
        notion_field_name=row["notion_field_name"],
        timestamp=row["timestamp"].isoformat() # Ensure datetime is ISO string
    )

@mcp.tool()
async def get_citations_for_document(source_document_fingerprint: str) -> Dict[str, Any]:
    """Retrieves all citations associated with a given source document fingerprint."""
    print(f"[CitationTracker] Received get_citations_for_document request: {source_document_fingerprint}")
    if not psycopg2 or not DATABASE_URL:
        return {"error": "Database support not available.", "status": "failure", "citations": []}

    query_sql = "SELECT * FROM citations WHERE source_document_fingerprint = %s;"
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur: # Use DictCursor
                cur.execute(query_sql, (source_document_fingerprint,))
                rows = cur.fetchall()

        citations = [_map_row_to_citation(dict(row)) for row in rows]
        print(f"[CitationTracker] Found {len(citations)} citations for document fingerprint {source_document_fingerprint}.")
        return {"citations": citations, "status": "success"}
    except ConnectionError as e:
        return {"error": f"Database connection error: {e}", "status": "failure", "citations": []}
    except psycopg2.Error as e:
        error_msg = f"Database error retrieving citations for document: {e}"
        print(f"[CitationTracker] {error_msg}")
        return {"error": error_msg, "status": "failure", "citations": []}
    except Exception as e:
        error_msg = f"Unexpected error retrieving citations for document: {e}"
        print(f"[CitationTracker] {error_msg}")
        return {"error": error_msg, "status": "failure", "citations": []}


@mcp.tool()
async def get_citations_for_notion_page(notion_page_id: str) -> Dict[str, Any]:
    """Retrieves all citations associated with a given Notion page ID."""
    print(f"[CitationTracker] Received get_citations_for_notion_page request: {notion_page_id}")
    if not psycopg2 or not DATABASE_URL:
        return {"error": "Database support not available.", "status": "failure", "citations": []}

    query_sql = "SELECT * FROM citations WHERE notion_page_id = %s;"
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur: # Use DictCursor
                cur.execute(query_sql, (notion_page_id,))
                rows = cur.fetchall()

        citations = [_map_row_to_citation(dict(row)) for row in rows]
        print(f"[CitationTracker] Found {len(citations)} citations for Notion page ID {notion_page_id}.")
        return {"citations": citations, "status": "success"}
    except ConnectionError as e:
        return {"error": f"Database connection error: {e}", "status": "failure", "citations": []}
    except psycopg2.Error as e:
        error_msg = f"Database error retrieving citations for Notion page: {e}"
        print(f"[CitationTracker] {error_msg}")
        return {"error": error_msg, "status": "failure", "citations": []}
    except Exception as e:
        error_msg = f"Unexpected error retrieving citations for Notion page: {e}"
        print(f"[CitationTracker] {error_msg}")
        return {"error": error_msg, "status": "failure", "citations": []}


if __name__ == "__main__":
    print("Citation Tracker MCP Server starting...")

    # Initialize the database (create table if it doesn't exist)
    db_init_success = init_citation_db()

    if not db_init_success:
        print("CRITICAL: Database initialization failed. Server might not function correctly.")
        # Depending on desired behavior, you might exit here if DB is essential
        # For now, it will continue and tools will return errors if DB is unavailable.

    # Example local tests (commented out, require DATABASE_URL to be set in .env)
    # async def run_citation_tests():
    #     if not db_init_success:
    #         print("Skipping citation tests due to DB init failure.")
    #         return

    #     print("\n--- Testing track_extraction ---")
    #     test_doc_fingerprint = "test_doc_hash_123"
    #     test_location = {"document_id": "doc_abc", "page_number": 1, "paragraph_number": 3}
    #     track_result = await track_extraction(
    #         source_document_fingerprint=test_doc_fingerprint,
    #         original_extracted_text="This is a test fact.",
    #         document_location=test_location,
    #         notion_page_id="notion_page_test_1",
    #         notion_field_name="achievements"
    #     )
    #     print(f"Track Result: {track_result}")
    #     citation_id_to_query = track_result.get("citation_id")

    #     if track_result["status"] == "success":
    #         print("\n--- Testing get_citations_for_document ---")
    #         doc_citations_result = await get_citations_for_document(source_document_fingerprint=test_doc_fingerprint)
    #         print(f"Doc Citations Result: {json.dumps(doc_citations_result, indent=2)}")

    #         print("\n--- Testing get_citations_for_notion_page ---")
    #         notion_citations_result = await get_citations_for_notion_page(notion_page_id="notion_page_test_1")
    #         print(f"Notion Citations Result: {json.dumps(notion_citations_result, indent=2)}")

    # if os.getenv("DATABASE_URL"):
    #    import asyncio
    #    asyncio.run(run_citation_tests())
    # else:
    #    print("DATABASE_URL not set. Skipping local citation tool tests.")

    mcp.run(transport="stdio")
