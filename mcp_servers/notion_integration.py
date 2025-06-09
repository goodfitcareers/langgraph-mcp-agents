"""
Notion Integration MCP Server
Handles professional history database operations in Notion
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from notion_client import Client
from fuzzywuzzy import fuzz
import mcp
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Notion client
notion = Client(auth=os.getenv("NOTION_TOKEN"))
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# Fuzzy matching threshold for role matching
FUZZY_MATCH_THRESHOLD = 80

# Initialize FastMCP server
mcp = FastMCP(
    "NotionIntegration",
    instructions="Notion database integration for professional history management",
    host="localhost",
    port=8003,
)

@mcp.tool()
async def query_existing_roles(client_name: str, limit: int = 100) -> Dict[str, Any]:
    """
    Fetch all existing roles for a client from the Notion database.
    
    Args:
        client_name (str): Name of the client to query roles for
        limit (int): Maximum number of roles to return
    
    Returns:
        Dict containing the roles and query metadata
    """
    
    result = {
        "success": False,
        "roles": [],
        "total_count": 0,
        "client_name": client_name,
        "error": "",
        "query_timestamp": datetime.now().isoformat()
    }
    
    try:
        # Query the Notion database
        query_filter = {
            "property": "Client",
            "title": {"equals": client_name}
        }
        
        response = notion.databases.query(
            database_id=DATABASE_ID,
            filter=query_filter,
            page_size=limit
        )
        
        roles = []
        for page in response["results"]:
            role = _parse_notion_page_to_role(page)
            if role:
                roles.append(role)
        
        result.update({
            "success": True,
            "roles": roles,
            "total_count": len(roles),
            "has_more": response.get("has_more", False),
            "next_cursor": response.get("next_cursor")
        })
        
        logger.info(f"Successfully queried {len(roles)} roles for client: {client_name}")
        
    except Exception as e:
        result["error"] = f"Query failed: {str(e)}"
        logger.error(f"Failed to query roles for {client_name}: {e}")
    
    return result

@mcp.tool()
async def create_or_update_role(
    role_data: Dict[str, Any], 
    citations: List[Dict[str, Any]], 
    client_name: str,
    existing_role_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new role or update an existing one in Notion.
    
    Args:
        role_data (Dict): Role information to save
        citations (List): Citation information for the role
        client_name (str): Name of the client
        existing_role_id (Optional[str]): ID of existing role to update
    
    Returns:
        Dict containing operation results
    """
    
    result = {
        "success": False,
        "page_id": "",
        "action": "",
        "error": "",
        "operation_timestamp": datetime.now().isoformat()
    }
    
    try:
        # Prepare Notion properties
        notion_properties = _prepare_notion_properties(role_data, client_name)
        
        if existing_role_id:
            # Update existing page
            response = notion.pages.update(
                page_id=existing_role_id,
                properties=notion_properties
            )
            result["action"] = "updated"
            logger.info(f"Updated existing role: {existing_role_id}")
            
        else:
            # Create new page
            response = notion.pages.create(
                parent={"database_id": DATABASE_ID},
                properties=notion_properties
            )
            result["action"] = "created"
            logger.info(f"Created new role for {client_name}")
        
        page_id = response["id"]
        
        # Add citations as page content
        if citations:
            await _add_citations_to_page(page_id, citations, role_data)
        
        result.update({
            "success": True,
            "page_id": page_id,
            "url": response["url"]
        })
        
    except Exception as e:
        result["error"] = f"Create/update operation failed: {str(e)}"
        logger.error(f"Failed to create/update role for {client_name}: {e}")
    
    return result

@mcp.tool()
async def find_role_matches(
    extracted_roles: List[Dict[str, Any]], 
    existing_roles: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Find matches between extracted roles and existing Notion entries.
    
    Args:
        extracted_roles (List): Roles extracted from resume
        existing_roles (List): Existing roles from Notion
    
    Returns:
        Dict containing match results
    """
    
    result = {
        "matches": [],
        "new_roles": [],
        "match_summary": {
            "total_extracted": len(extracted_roles),
            "total_existing": len(existing_roles),
            "matched_count": 0,
            "new_count": 0
        }
    }
    
    try:
        for extracted_role in extracted_roles:
            best_match = None
            best_score = 0
            
            for existing_role in existing_roles:
                match_score = _calculate_role_match_score(extracted_role, existing_role)
                
                if match_score > best_score and match_score >= FUZZY_MATCH_THRESHOLD:
                    best_score = match_score
                    best_match = existing_role
            
            if best_match:
                # Found a match
                match_info = {
                    "extracted_role": extracted_role,
                    "existing_role": best_match,
                    "match_score": best_score,
                    "suggested_updates": _generate_role_diff(extracted_role, best_match)
                }
                result["matches"].append(match_info)
                result["match_summary"]["matched_count"] += 1
                
            else:
                # No match found - this is a new role
                result["new_roles"].append(extracted_role)
                result["match_summary"]["new_count"] += 1
        
        logger.info(f"Role matching complete: {result['match_summary']['matched_count']} matches, {result['match_summary']['new_count']} new roles")
        
    except Exception as e:
        logger.error(f"Role matching failed: {e}")
        result["error"] = str(e)
    
    return result

@mcp.tool()
async def delete_role(page_id: str, reason: str = "User requested deletion") -> Dict[str, Any]:
    """
    Archive/delete a role from Notion.
    
    Args:
        page_id (str): Notion page ID to delete
        reason (str): Reason for deletion
    
    Returns:
        Dict containing deletion results
    """
    
    result = {
        "success": False,
        "page_id": page_id,
        "error": "",
        "deletion_timestamp": datetime.now().isoformat()
    }
    
    try:
        # Archive the page (Notion doesn't support true deletion via API)
        notion.pages.update(
            page_id=page_id,
            archived=True
        )
        
        # Add deletion reason to the page
        notion.blocks.children.append(
            block_id=page_id,
            children=[{
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {
                            "content": f"ARCHIVED: {reason} (Timestamp: {datetime.now().isoformat()})"
                        }
                    }]
                }
            }]
        )
        
        result["success"] = True
        logger.info(f"Successfully archived role: {page_id}")
        
    except Exception as e:
        result["error"] = f"Deletion failed: {str(e)}"
        logger.error(f"Failed to delete role {page_id}: {e}")
    
    return result

@mcp.tool()
async def get_database_schema() -> Dict[str, Any]:
    """
    Retrieve the current Notion database schema.
    
    Returns:
        Dict containing database schema information
    """
    
    try:
        database = notion.databases.retrieve(database_id=DATABASE_ID)
        
        schema = {
            "database_id": DATABASE_ID,
            "title": database["title"][0]["text"]["content"] if database["title"] else "Unknown",
            "properties": {},
            "url": database["url"]
        }
        
        for prop_name, prop_config in database["properties"].items():
            schema["properties"][prop_name] = {
                "type": prop_config["type"],
                "id": prop_config["id"]
            }
            
            # Add additional config for specific types
            if prop_config["type"] == "select":
                schema["properties"][prop_name]["options"] = [
                    option["name"] for option in prop_config.get("select", {}).get("options", [])
                ]
        
        return {"success": True, "schema": schema}
        
    except Exception as e:
        logger.error(f"Failed to retrieve database schema: {e}")
        return {"success": False, "error": str(e)}

def _parse_notion_page_to_role(page: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse a Notion page into a standardized role dictionary."""
    
    try:
        properties = page["properties"]
        
        role = {
            "notion_id": page["id"],
            "url": page["url"],
            "created_time": page["created_time"],
            "last_edited_time": page["last_edited_time"],
            
            # Extract property values
            "company": _extract_text_property(properties.get("Company")),
            "title": _extract_text_property(properties.get("Title")),
            "start_year": _extract_number_property(properties.get("Start Year")),
            "end_year": _extract_number_property(properties.get("End Year")),
            "start_month": _extract_number_property(properties.get("Start Month")),
            "end_month": _extract_number_property(properties.get("End Month")),
            "manager_title": _extract_text_property(properties.get("Manager Title")),
            "budget_responsibility": _extract_number_property(properties.get("Budget Responsibility")),
            "headcount": _extract_number_property(properties.get("Headcount")),
            "quota": _extract_number_property(properties.get("Quota")),
            "location": _extract_text_property(properties.get("Location")),
            "employment_type": _extract_select_property(properties.get("Employment Type")),
            "client": _extract_text_property(properties.get("Client")),
        }
        
        return role
        
    except Exception as e:
        logger.warning(f"Failed to parse Notion page {page.get('id', 'unknown')}: {e}")
        return None

def _prepare_notion_properties(role_data: Dict[str, Any], client_name: str) -> Dict[str, Any]:
    """Prepare role data for Notion page properties."""
    
    properties = {
        "Client": {"title": [{"text": {"content": client_name}}]},
        "Company": {"rich_text": [{"text": {"content": role_data.get("company", "")}}]},
        "Title": {"rich_text": [{"text": {"content": role_data.get("title", "")}}]},
    }
    
    # Add numeric properties
    if role_data.get("start_year"):
        properties["Start Year"] = {"number": role_data["start_year"]}
    if role_data.get("end_year"):
        properties["End Year"] = {"number": role_data["end_year"]}
    if role_data.get("start_month"):
        properties["Start Month"] = {"number": role_data["start_month"]}
    if role_data.get("end_month"):
        properties["End Month"] = {"number": role_data["end_month"]}
    if role_data.get("budget_responsibility"):
        properties["Budget Responsibility"] = {"number": role_data["budget_responsibility"]}
    if role_data.get("headcount"):
        properties["Headcount"] = {"number": role_data["headcount"]}
    if role_data.get("quota"):
        properties["Quota"] = {"number": role_data["quota"]}
    
    # Add text properties
    if role_data.get("manager_title"):
        properties["Manager Title"] = {"rich_text": [{"text": {"content": role_data["manager_title"]}}]}
    if role_data.get("location"):
        properties["Location"] = {"rich_text": [{"text": {"content": role_data["location"]}}]}
    
    # Add select property
    if role_data.get("employment_type"):
        properties["Employment Type"] = {"select": {"name": role_data["employment_type"]}}
    
    return properties

async def _add_citations_to_page(page_id: str, citations: List[Dict[str, Any]], role_data: Dict[str, Any]):
    """Add citation information as blocks to the Notion page."""
    
    try:
        blocks = []
        
        # Add role details section
        if role_data.get("achievements"):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Key Achievements"}}]
                }
            })
            
            for achievement in role_data["achievements"]:
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": achievement}}]
                    }
                })
        
        if role_data.get("responsibilities"):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Key Responsibilities"}}]
                }
            })
            
            for responsibility in role_data["responsibilities"]:
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": responsibility}}]
                    }
                })
        
        # Add citations section
        if citations:
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Source Citations"}}]
                }
            })
            
            for citation in citations:
                citation_text = f"Document: {citation.get('document_id', 'Unknown')}"
                if citation.get('page_number'):
                    citation_text += f", Page: {citation['page_number']}"
                if citation.get('confidence_score'):
                    citation_text += f", Confidence: {citation['confidence_score']:.2f}"
                
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": citation_text}}]
                    }
                })
        
        # Add blocks to the page
        if blocks:
            notion.blocks.children.append(block_id=page_id, children=blocks)
            
    except Exception as e:
        logger.error(f"Failed to add citations to page {page_id}: {e}")

def _calculate_role_match_score(role1: Dict[str, Any], role2: Dict[str, Any]) -> int:
    """Calculate similarity score between two roles."""
    
    company_score = fuzz.ratio(
        role1.get("company", "").lower(),
        role2.get("company", "").lower()
    )
    
    title_score = fuzz.ratio(
        role1.get("title", "").lower(),
        role2.get("title", "").lower()
    )
    
    # Date overlap scoring
    date_score = 0
    if role1.get("start_year") and role2.get("start_year"):
        year_diff = abs(role1["start_year"] - role2["start_year"])
        if year_diff <= 1:
            date_score = 100 - (year_diff * 10)
    
    # Weighted average
    total_score = (company_score * 0.4 + title_score * 0.4 + date_score * 0.2)
    return int(total_score)

def _generate_role_diff(extracted: Dict[str, Any], existing: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a diff of changes between extracted and existing role."""
    
    diff = {"updates": {}, "additions": {}}
    
    # Compare all fields
    fields_to_compare = [
        "title", "start_year", "end_year", "start_month", "end_month",
        "manager_title", "budget_responsibility", "headcount", "quota",
        "location", "employment_type"
    ]
    
    for field in fields_to_compare:
        extracted_val = extracted.get(field)
        existing_val = existing.get(field)
        
        if extracted_val and extracted_val != existing_val:
            if existing_val:
                diff["updates"][field] = {
                    "from": existing_val,
                    "to": extracted_val
                }
            else:
                diff["additions"][field] = extracted_val
    
    # Handle list fields
    list_fields = ["achievements", "responsibilities", "direct_reports", "peer_functions"]
    for field in list_fields:
        extracted_list = extracted.get(field, [])
        if extracted_list:
            diff["additions"][field] = extracted_list
    
    return diff

def _extract_text_property(prop: Optional[Dict]) -> str:
    """Extract text from Notion text property."""
    if not prop:
        return ""
    
    if prop["type"] == "title" and prop["title"]:
        return prop["title"][0]["text"]["content"]
    elif prop["type"] == "rich_text" and prop["rich_text"]:
        return prop["rich_text"][0]["text"]["content"]
    
    return ""

def _extract_number_property(prop: Optional[Dict]) -> Optional[int]:
    """Extract number from Notion number property."""
    if prop and prop["type"] == "number":
        return prop["number"]
    return None

def _extract_select_property(prop: Optional[Dict]) -> str:
    """Extract select value from Notion select property."""
    if prop and prop["type"] == "select" and prop["select"]:
        return prop["select"]["name"]
    return ""

if __name__ == "__main__":
    logger.info("Starting Notion Integration MCP Server...")
    mcp.run(transport="stdio") 