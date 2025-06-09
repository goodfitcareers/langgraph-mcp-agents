import streamlit as st
import asyncio
import pandas as pd
from typing import TYPE_CHECKING, List, Dict, Any, Optional
import os # For environment variables

# Assuming MultiServerMCPClient and load_mcp_config are accessible
# This might mean moving load_mcp_config to a shared utils or importing from pipeline
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    # If load_mcp_config is in workflow.pipeline, ensure it's importable
    # For simplicity, if it's not easily importable, we might duplicate or simplify config loading here.
    # Let's assume it can be imported or is moved to a shared location.
    from workflow.pipeline import load_mcp_config
except ImportError:
    st.error("Critical component MultiServerMCPClient or load_mcp_config not found. Database tab may not work.")
    MultiServerMCPClient = None
    load_mcp_config = None


if TYPE_CHECKING:
    from workflow.pipeline import ResumeProcessingWorkflow


async def fetch_notion_data() -> Optional[List[Dict[str, Any]]]:
    """
    Fetches all roles from the Notion database using the notion_integration MCP server.
    Manages its own MCP client.
    """
    if not MultiServerMCPClient or not load_mcp_config:
        st.error("MCP client or config loader not available for fetching Notion data.")
        return None

    # Check for necessary environment variables
    if not os.getenv("NOTION_TOKEN") or not os.getenv("NOTION_DATABASE_ID"):
        st.error("NOTION_TOKEN or NOTION_DATABASE_ID environment variables are not set. Cannot connect to Notion.")
        return None

    mcp_config = None
    try:
        mcp_config = load_mcp_config()
    except Exception as e:
        st.error(f"Failed to load MCP configuration: {e}")
        return None

    if not mcp_config or "notion_integration" not in mcp_config:
        st.error("Notion integration server details not found in MCP configuration.")
        return None

    # Ensure the security_gateway config is present if _call_mcp_tool_direct expects it.
    # For direct call to notion_integration, SG might not be strictly needed by this UI function.
    # However, the _call_mcp_tool_direct (if copied/adapted) might attempt to use it.

    async with MultiServerMCPClient(mcp_config) as client:
        try:
            # This is a direct call to the notion_integration server.
            # If a security gateway is mandatory for all calls, this would need to go through it.
            # For simplicity, assuming direct call is fine for querying data for display.
            # The _call_mcp_tool from workflow includes SG logic, but that's for graph nodes.
            # We can use a simplified version or call directly.

            print("[DatabaseUI] Calling notion_integration.query_existing_roles")
            response = await client.call_tool("notion_integration", "query_existing_roles", {})

            if response and isinstance(response, dict) and response.get("status") == "success":
                print(f"[DatabaseUI] Successfully fetched {len(response.get('roles', []))} roles.")
                return response.get("roles", [])
            else:
                error_msg = response.get("error", "Unknown error fetching data from Notion.")
                st.error(f"Failed to fetch data from Notion: {error_msg}")
                print(f"[DatabaseUI] Error: {error_msg}")
                return None
        except Exception as e:
            st.error(f"An exception occurred while fetching Notion data: {e}")
            print(f"[DatabaseUI] Exception: {e}")
            return None


def render_database_tab(workflow_runner: Optional["ResumeProcessingWorkflow"] = None): # workflow_runner might not be needed if this tab is self-contained
    """
    Renders the UI for the View Database tab.
    Allows users to fetch and view data from the Notion database.
    """
    st.header("View Professional History Database (Notion)")

    if st.button("🔄 Refresh Data from Notion", key="refresh_notion_data"):
        with st.spinner("Fetching data from Notion..."):
            # Use asyncio.run for the async function call from Streamlit's sync context
            roles_data = asyncio.run(fetch_notion_data())
            if roles_data is not None:
                st.session_state.notion_data_view = roles_data
                st.success(f"Successfully fetched {len(roles_data)} roles from Notion.")
            else:
                # Error messages are handled within fetch_notion_data
                st.session_state.notion_data_view = [] # Clear or keep old data on error? Clearing for now.

    if 'notion_data_view' not in st.session_state:
        st.info("Click 'Refresh Data from Notion' to load entries.")
        st.session_state.notion_data_view = [] # Initialize if not present

    if not st.session_state.notion_data_view:
        st.write("No data to display. Ensure Notion database has entries and click 'Refresh Data'.")
        return

    # Display data using Pandas DataFrame
    try:
        df = pd.DataFrame(st.session_state.notion_data_view)

        # Select and rename columns for a cleaner display
        display_columns_map = {
            "company": "Company",
            "title": "Title",
            "start_year": "Start Year",
            "end_year": "End Year",
            "manager_title": "Manager Title",
            "last_updated": "Last Updated",
            "notion_page_id": "Notion Page ID"
            # Add other simple fields you want in the main table
        }

        # Filter DataFrame to include only desired columns
        display_df = df[list(display_columns_map.keys())].copy() # Use .copy() to avoid SettingWithCopyWarning
        display_df.rename(columns=display_columns_map, inplace=True)

        st.info(f"Displaying {len(display_df)} roles fetched from Notion.")
        st.dataframe(display_df, use_container_width=True)

        st.subheader("Detailed View")
        if not df.empty:
            # Show details for each role in an expander
            for index, row in df.iterrows():
                company = row.get('company', 'N/A')
                title = row.get('title', 'N/A')
                expander_title = f"{title} at {company} (ID: {row.get('notion_page_id', 'N/A')[:8]}...)"
                with st.expander(expander_title):
                    st.json(row.to_dict(), expanded=False) # Show all data as JSON in expander
                    # Or display specific fields like achievements/responsibilities more nicely:
                    # st.markdown("##### Achievements")
                    # for ach in row.get('achievements', []): st.markdown(f"- {ach}")
                    # st.markdown("##### Responsibilities")
                    # for resp in row.get('responsibilities', []): st.markdown(f"- {resp}")
        else:
            st.write("No detailed data to display.")

    except Exception as e:
        st.error(f"An error occurred while preparing data for display: {e}")
        st.write("Raw data (if available):")
        st.json(st.session_state.notion_data_view[:5], expanded=False) # Display first 5 items raw
