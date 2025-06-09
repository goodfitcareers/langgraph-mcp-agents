import os
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, TypedDict, Union

from dotenv import load_dotenv
from mcp.server import FastMCP, tool

# Attempt to import Notion client
try:
    import notion_client
    from notion_client.helpers import get_rich_text_plain_text, get_property_value
except ImportError:
    notion_client = None
    get_rich_text_plain_text = None
    get_property_value = None
    print("CRITICAL: notion_client library not found. Notion integration will not be available.")

# Load environment variables
load_dotenv(override=True)

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# Initialize Notion Client
notion = None
if notion_client and NOTION_TOKEN:
    try:
        notion = notion_client.Client(auth=NOTION_TOKEN)
    except Exception as e:
        print(f"Error initializing Notion client: {e}")
        notion = None
elif not notion_client:
    print("Notion library not installed, Notion features disabled.")
elif not NOTION_TOKEN:
    print("NOTION_TOKEN not found in environment variables, Notion features disabled.")

# --- Type Definitions ---

class NotionProfessionalHistorySchema(TypedDict, total=False):
    notion_page_id: Optional[str] # To store the Notion page ID
    company: str # Text (Title in Notion for simplicity, or a dedicated Text property)
    title: str # Text
    start_year: Optional[int] # Number
    end_year: Optional[Union[int, str]] # Number or Text "Present"
    manager_title: Optional[str] # Text
    direct_reports: Optional[Union[int, str]] # Number or Text for ranges/notes
    budget_responsibility: Optional[Union[float, str]] # Number or Text
    headcount: Optional[int] # Number
    quota: Optional[Union[float, str]] # Number or Text
    peer_functions: Optional[List[str]] # Multi-select or JSON string in Text
    achievements: Optional[List[str]] # JSON string in Text (or Rich Text with bullets)
    responsibilities: Optional[List[str]] # JSON string in Text (or Rich Text with bullets)
    sources: Optional[List[Dict[str, str]]] # JSON string in Text
    confidence_score: Optional[float] # Number
    last_updated: str # Date or Text (ISO format datetime string)

# --- MCP Server Definition ---
mcp = FastMCP(
    name="NotionIntegration",
    description="Manages professional history data in a Notion database.",
    instructions=(
        "Use this server to query existing professional roles from Notion or "
        "to add/update role information in the Notion database."
    )
)

# --- Helper Functions ---

def _format_rich_text(text: Optional[str]) -> List[Dict[str, Any]]:
    """Helper to create Notion rich_text structure from a plain string."""
    if text is None:
        return []
    return [{"type": "text", "text": {"content": text}}]

def _format_list_as_json_string(data: Optional[List[Any]]) -> Optional[str]:
    """Helper to format a list as a JSON string for storing in a Notion text field."""
    if data is None:
        return None
    return json.dumps(data)

def _parse_json_string_from_rich_text(property_value: Any, default: Optional[List[Any]] = None) -> Optional[List[Any]]:
    """Helper to parse a JSON string from a Notion rich_text property."""
    if default is None:
        default = []
    plain_text = get_rich_text_plain_text(property_value)
    if plain_text:
        try:
            return json.loads(plain_text)
        except json.JSONDecodeError:
            # If not valid JSON, perhaps it's a simple string list separated by newlines or commas
            # For MVP, we'll assume it should be JSON if populated.
            print(f"Warning: Could not parse JSON from rich_text: {plain_text}")
            return default # Or handle as plain text / split by lines
    return default

def map_notion_page_to_schema(page: Dict[str, Any]) -> NotionProfessionalHistorySchema:
    """Maps a Notion page object to NotionProfessionalHistorySchema."""
    props = page.get("properties", {})

    # Handle potential "Present" string for end_year
    end_year_val = get_property_value(props.get("End Year"))
    if isinstance(end_year_val, str) and end_year_val.lower() == "present":
        end_year_processed = "Present"
    elif isinstance(end_year_val, (int, float)): # float if Notion returns number like X.0
        end_year_processed = int(end_year_val)
    else: # Could be None or other unexpected type
        end_year_processed = None

    schema_data: NotionProfessionalHistorySchema = {
        "notion_page_id": page.get("id"),
        "company": get_rich_text_plain_text(props.get("Company")), # Assuming 'Company' is Title or Rich Text
        "title": get_rich_text_plain_text(props.get("Title")),
        "start_year": get_property_value(props.get("Start Year")),
        "end_year": end_year_processed,
        "manager_title": get_rich_text_plain_text(props.get("Manager Title")),
        "direct_reports": get_property_value(props.get("Direct Reports")), # Could be number or text
        "budget_responsibility": get_property_value(props.get("Budget Responsibility")), # Number or text
        "headcount": get_property_value(props.get("Headcount")),
        "quota": get_property_value(props.get("Quota")), # Number or text
        "peer_functions": _parse_json_string_from_rich_text(props.get("Peer Functions"), []),
        "achievements": _parse_json_string_from_rich_text(props.get("Achievements"), []),
        "responsibilities": _parse_json_string_from_rich_text(props.get("Responsibilities"), []),
        "sources": _parse_json_string_from_rich_text(props.get("Sources"), []),
        "confidence_score": get_property_value(props.get("Confidence Score")),
        "last_updated": get_property_value(props.get("Last Updated")) # Assumes Date or ISO string in Text
    }
    # Filter out None values if not desired in the output for optional fields
    return {k: v for k, v in schema_data.items() if v is not None}


def map_schema_to_notion_properties(data: NotionProfessionalHistorySchema) -> Dict[str, Any]:
    """Constructs the properties dictionary for Notion API from schema data."""
    properties = {}

    # Title property in Notion is special. Assuming 'Company' is the Title property.
    if "company" in data and data["company"]:
        properties["Company"] = {"title": _format_rich_text(data["company"])} # Main page title

    # Standard properties
    if "title" in data:
        properties["Title"] = {"rich_text": _format_rich_text(data.get("title"))}
    if "start_year" in data and data["start_year"] is not None:
        properties["Start Year"] = {"number": int(data["start_year"])}

    end_year = data.get("end_year")
    if end_year is not None:
        if isinstance(end_year, str) and end_year.lower() == "present":
            properties["End Year"] = {"rich_text": _format_rich_text("Present")} # Store "Present" as text
        elif isinstance(end_year, (int, float)):
            properties["End Year"] = {"number": int(end_year)}
        # else, if it's some other string not "Present", it might be an error or needs specific handling

    if "manager_title" in data:
        properties["Manager Title"] = {"rich_text": _format_rich_text(data.get("manager_title"))}

    # Handling for fields that can be number or text
    for key, notion_key in [
        ("direct_reports", "Direct Reports"),
        ("budget_responsibility", "Budget Responsibility"),
        ("quota", "Quota")
    ]:
        value = data.get(key)
        if value is not None:
            if isinstance(value, (int, float)):
                properties[notion_key] = {"number": value}
            else: # Assume string
                properties[notion_key] = {"rich_text": _format_rich_text(str(value))}

    if "headcount" in data and data["headcount"] is not None:
        properties["Headcount"] = {"number": int(data["headcount"])}

    # List-like fields stored as JSON strings in Text properties
    for key, notion_key in [
        ("peer_functions", "Peer Functions"),
        ("achievements", "Achievements"),
        ("responsibilities", "Responsibilities"),
        ("sources", "Sources")
    ]:
        list_data = data.get(key)
        if list_data is not None: # Even an empty list should be stored if provided
             properties[notion_key] = {"rich_text": _format_rich_text(_format_list_as_json_string(list_data))}


    if "confidence_score" in data and data["confidence_score"] is not None:
        properties["Confidence Score"] = {"number": float(data["confidence_score"])}

    # Last Updated - using ISO format string for a Date property or Text
    # Notion Date property expects {"date": {"start": "YYYY-MM-DDTHH:MM:SSZ"}}
    last_updated_iso = data.get("last_updated", datetime.now(timezone.utc).isoformat())
    properties["Last Updated"] = {"date": {"start": last_updated_iso}}

    return properties

# --- MCP Tools ---

@mcp.tool()
async def query_existing_roles(client_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Queries all professional history roles from the Notion database.
    `client_id` is for future use.
    """
    print(f"[NotionIntegration] Received query_existing_roles request. Client ID: {client_id}")
    if not notion or not NOTION_DATABASE_ID:
        return {"error": "Notion client or Database ID not configured.", "status": "failure", "roles": []}

    try:
        response = notion.databases.query(database_id=NOTION_DATABASE_ID)
        roles = [map_notion_page_to_schema(page) for page in response.get("results", [])]
        print(f"[NotionIntegration] Successfully queried {len(roles)} roles.")
        return {"roles": roles, "status": "success"}
    except Exception as e:
        error_msg = f"Error querying Notion database: {e}"
        print(f"[NotionIntegration] {error_msg}")
        return {"error": error_msg, "status": "failure", "roles": []}


@mcp.tool()
async def add_professional_role(role_data: Dict[str, Any], citations: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Adds a new professional role to the Notion database.
    `role_data` should conform to NotionProfessionalHistorySchema.
    `citations` will be merged into `role_data['sources']`.
    """
    print(f"[NotionIntegration] Received add_professional_role request.")
    if not notion or not NOTION_DATABASE_ID:
        return {"error": "Notion client or Database ID not configured.", "status": "failure"}

    # Ensure role_data is a valid dictionary
    if not isinstance(role_data, dict):
        return {"error": "role_data must be a dictionary.", "status": "failure"}

    # Type cast to schema for helper compatibility, actual validation might be needed
    schema_data: NotionProfessionalHistorySchema = NotionProfessionalHistorySchema(**role_data)

    if citations:
        existing_sources = schema_data.get("sources", [])
        if not isinstance(existing_sources, list): # Should be a list from schema
            existing_sources = []
        schema_data["sources"] = existing_sources + citations

    # Ensure last_updated is set
    if "last_updated" not in schema_data or not schema_data["last_updated"]:
        schema_data["last_updated"] = datetime.now(timezone.utc).isoformat()

    # Ensure company (assumed to be Notion's primary "Title" column) exists
    if not schema_data.get("company"):
        return {"error": "Company name (primary field for Notion page title) is required.", "status": "failure"}

    try:
        notion_properties = map_schema_to_notion_properties(schema_data)

        new_page = notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties=notion_properties
        )
        new_page_id = new_page.get("id")
        print(f"[NotionIntegration] Successfully created new role page with ID: {new_page_id}")
        return {"notion_page_id": new_page_id, "status": "success"}
    except Exception as e:
        error_msg = f"Error creating Notion page: {e}"
        print(f"[NotionIntegration] {error_msg}")
        # You might want to inspect `e` further if it's a NotionAPIError for more details
        if hasattr(e, 'body'): # NotionClientAPIError often has a body
            error_msg += f" - Notion API Response: {getattr(e, 'body')}"
        return {"error": error_msg, "status": "failure"}

# For MVP, update_role_information will be simplified to add_professional_role.
# A true update would require notion_page_id and use notion.pages.update().
# Renaming the tool for clarity in MVP.
# If you need distinct update later, you can add:
# @mcp.tool()
# async def update_existing_role(role_data: Dict[str, Any]) -> Dict[str, Any]:
#     if not role_data.get("notion_page_id"):
#         return {"error": "notion_page_id is required for updating.", "status": "failure"}
#     page_id = role_data["notion_page_id"]
#     # ... logic for notion.pages.update(page_id=page_id, properties=...) ...


if __name__ == "__main__":
    print("Notion Integration MCP Server starting...")
    # Example of how to test locally (requires Notion token and DB ID to be set in .env)
    # These are illustrative and assume your Notion DB has matching property names/types.

    # async def run_tests():
    #     if not notion or not NOTION_DATABASE_ID:
    #         print("Skipping tests: Notion client or DB ID not configured.")
    #         return

    #     print("\n--- Testing query_existing_roles ---")
    #     query_result = await query_existing_roles()
    #     print(f"Query Result: {json.dumps(query_result, indent=2)}")

    #     if query_result["status"] == "success" and query_result["roles"]:
    #         print(f"\nSuccessfully fetched {len(query_result['roles'])} roles.")
    #         # print(f"First role: {query_result['roles'][0]}")


    #     print("\n--- Testing add_professional_role ---")
    #     sample_role_data = {
    #         "company": "TestCo from MCP " + datetime.now().strftime("%H:%M:%S"),
    #         "title": "MCP Test Engineer",
    #         "start_year": 2023,
    #         "end_year": "Present",
    #         "achievements": ["Tested MCP integration.", "Wrote sample data script."],
    #         "responsibilities": ["Ensure quality.", "Automate testing."],
    #         "peer_functions": ["Development", "Product"],
    #         "confidence_score": 0.95,
    #         # "last_updated" will be set by the tool if not provided
    #     }
    #     add_result = await add_professional_role(role_data=sample_role_data, citations=[{"doc_id": "test_doc", "detail": "page 1"}])
    #     print(f"Add Result: {json.dumps(add_result, indent=2)}")

    #     if add_result["status"] == "success":
    #         print(f"Successfully added role with page ID: {add_result['notion_page_id']}")
    #         # You could add a notion.pages.update here to archive/delete the test page
    #         # notion.pages.update(page_id=add_result['notion_page_id'], archived=True)


    # if os.getenv("NOTION_TOKEN") and os.getenv("NOTION_DATABASE_ID"):
    #     import asyncio
    #     asyncio.run(run_tests())
    # else:
    #     print("NOTION_TOKEN and/or NOTION_DATABASE_ID not set. Skipping local tool tests.")

    mcp.run(transport="stdio")
