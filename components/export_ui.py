import streamlit as st
import asyncio
import pandas as pd
import json
from typing import TYPE_CHECKING, List, Dict, Any, Optional
import os

# Assuming MultiServerMCPClient and load_mcp_config are accessible
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from workflow.pipeline import load_mcp_config
except ImportError:
    st.error("Critical component MultiServerMCPClient or load_mcp_config not found. Export tab may not work.")
    MultiServerMCPClient = None
    load_mcp_config = None

if TYPE_CHECKING:
    from workflow.pipeline import ResumeProcessingWorkflow # Only for type hinting if passed

# Helper function to fetch Notion data (similar to database_ui.py)
async def fetch_notion_data_for_export() -> Optional[List[Dict[str, Any]]]:
    if not MultiServerMCPClient or not load_mcp_config:
        st.error("MCP client or config loader not available for fetching Notion data.")
        return None
    if not os.getenv("NOTION_TOKEN") or not os.getenv("NOTION_DATABASE_ID"):
        st.error("Notion environment variables not set.")
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

    async with MultiServerMCPClient(mcp_config) as client:
        try:
            response = await client.call_tool("notion_integration", "query_existing_roles", {})
            if response and isinstance(response, dict) and response.get("status") == "success":
                return response.get("roles", [])
            else:
                st.error(f"Failed to fetch Notion data: {response.get('error', 'Unknown error')}")
                return None
        except Exception as e:
            st.error(f"Exception fetching Notion data: {e}")
            return None

# Helper function to fetch all citations
async def fetch_all_citations_for_export() -> Optional[List[Dict[str, Any]]]:
    if not MultiServerMCPClient or not load_mcp_config:
        st.error("MCP client or config loader not available for fetching citations.")
        return None
    if not os.getenv("DATABASE_URL"): # Citation tracker needs DATABASE_URL
        st.error("DATABASE_URL environment variable not set for citation tracker.")
        return None

    mcp_config = None
    try:
        mcp_config = load_mcp_config()
    except Exception as e:
        st.error(f"Failed to load MCP configuration: {e}")
        return None

    if not mcp_config or "citation_tracker" not in mcp_config:
        st.error("Citation tracker server details not found in MCP configuration.")
        return None

    async with MultiServerMCPClient(mcp_config) as client:
        try:
            response = await client.call_tool("citation_tracker", "get_all_citations", {})
            if response and isinstance(response, dict) and response.get("status") == "success":
                return response.get("citations", [])
            else:
                st.error(f"Failed to fetch citations: {response.get('error', 'Unknown error')}")
                return None
        except Exception as e:
            st.error(f"Exception fetching citations: {e}")
            return None


def render_export_tab(workflow_runner: Optional["ResumeProcessingWorkflow"] = None):
    st.header("Export Processed Data")

    # --- Export Professional History from Notion ---
    st.subheader("Export Professional History from Notion")
    if st.button("Prepare Notion Data for Export", key="prepare_notion_export"):
        with st.spinner("Fetching Notion data for export..."):
            roles_data = asyncio.run(fetch_notion_data_for_export())
            if roles_data is not None:
                st.session_state.exportable_notion_data = roles_data
                st.success(f"Successfully fetched {len(roles_data)} roles from Notion for export.")
            else:
                st.session_state.exportable_notion_data = []

    if 'exportable_notion_data' in st.session_state and st.session_state.exportable_notion_data:
        try:
            df_roles = pd.DataFrame(st.session_state.exportable_notion_data)
            # Flatten lists/dicts if necessary for CSV, or keep as JSON strings
            for col in ['peer_functions', 'achievements', 'responsibilities', 'sources']:
                if col in df_roles.columns:
                    df_roles[col] = df_roles[col].apply(lambda x: json.dumps(x) if isinstance(x, (list, dict)) else x)

            csv_data = df_roles.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Professional History as CSV",
                data=csv_data,
                file_name="professional_history_export.csv",
                mime="text/csv",
                key="download_roles_csv"
            )
        except Exception as e:
            st.error(f"Error preparing roles CSV for download: {e}")

    # --- Export Citations ---
    st.subheader("Export Citations")
    if st.button("Prepare All Citations for Export", key="prepare_citations_export"):
        with st.spinner("Fetching all citations for export..."):
            citation_data = asyncio.run(fetch_all_citations_for_export())
            if citation_data is not None:
                st.session_state.exportable_citation_data = citation_data
                st.success(f"Successfully fetched {len(citation_data)} citations for export.")
            else:
                st.session_state.exportable_citation_data = []

    if 'exportable_citation_data' in st.session_state and st.session_state.exportable_citation_data:
        try:
            # For citations, JSON might be better due to nested structures like document_location
            json_data = json.dumps(st.session_state.exportable_citation_data, indent=2)
            st.download_button(
                label="Download All Citations as JSON",
                data=json_data,
                file_name="all_citations_export.json",
                mime="application/json",
                key="download_citations_json"
            )
        except Exception as e:
            st.error(f"Error preparing citations JSON for download: {e}")

    if 'latest_workflow_run' in st.session_state:
        st.sidebar.subheader("Export Data from Last Workflow Run")
        last_run_state = st.session_state.latest_workflow_run

        # Export entire state of last run
        try:
            state_json = json.dumps(last_run_state, default=lambda o: o.name if hasattr(o, 'name') and isinstance(o, Enum) else str(o) if isinstance(o, uuid.UUID) else None , indent=2) # Handle Enum and UUID
            st.sidebar.download_button(
                label="Download Last Run State (JSON)",
                data=state_json,
                file_name=f"workflow_state_{last_run_state.get('workflow_id', 'unknown_wf')}.json",
                mime="application/json",
                key="download_last_run_state_export_tab"
            )
        except Exception as e:
            st.sidebar.error(f"Error preparing last run state JSON: {e}")

    st.markdown("---")
    st.caption("Note: Ensure MCP servers (Notion Integration, Citation Tracker) are running for data preparation.")
```
