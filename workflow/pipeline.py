import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union

from langgraph.graph import StatefulGraph, END
from langgraph.checkpoint.memory import MemorySaver # For potential state persistence

# Assuming MultiServerMCPClient is designed to be used with async with
from langchain_mcp_adapters.client import MultiServerMCPClient

# State and type imports
from workflow.state import ResumeProcessingState, DocumentType

# Attempt to import types from document_processor, fallback to Any/Dict
# In a real project, these would be in a shared types module.
try:
    from mcp_servers.document_processor import ProfessionalHistory, ExtractedData
    # ProfessionalHistory is a TypedDict, ExtractedData is a TypedDict
except ImportError:
    print("Warning: Could not import ProfessionalHistory or ExtractedData from mcp_servers.document_processor. Using Dict[str, Any] as placeholder.")
    ProfessionalHistory = Dict[str, Any]
    ExtractedData = Dict[str, Any]


# --- Helper Function to Load MCP Config ---
def load_mcp_config(config_path: str = "resume_mcp_config.json") -> Dict[str, Any]:
    """Loads the MCP server configuration from the specified JSON file."""
    try:
        # Ensure the path is absolute or relative to the current file's directory if needed
        # For now, assume it's in the root or accessible via relative path from where app runs.
        if not os.path.exists(config_path):
            # Try path relative to this file's directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            rel_config_path = os.path.join(current_dir, "..", config_path) # Go up one level to project root
            if os.path.exists(rel_config_path):
                config_path = rel_config_path
            else:
                raise FileNotFoundError(f"MCP config file not found at {config_path} or {rel_config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: MCP configuration file '{config_path}' not found.")
        raise
    except json.JSONDecodeError:
        print(f"ERROR: Could not decode MCP configuration file '{config_path}'.")
        raise


class ResumeProcessingWorkflow:
    def __init__(self):
        self.mcp_config = load_mcp_config()
        # MCP client will be initialized and managed per `run` invocation using `async with`
        # This avoids issues with event loops if workflow instance is long-lived.
        self.mcp_client_instance = None # Placeholder if needed for other methods

        workflow = StatefulGraph[ResumeProcessingState](checkpointer=MemorySaver()) # Added checkpointer

        # Define nodes
        workflow.add_node("start", self.start_workflow)
        workflow.add_node("classify_document", self.classify_document_node)
        workflow.add_node("extract_information", self.extract_information_node)
        # TODO: Add more nodes: query_notion, match_roles, human_review_gate, process_updates, end_workflow

        # Define edges
        workflow.set_entry_point("start")
        workflow.add_edge("start", "classify_document")
        workflow.add_edge("classify_document", "extract_information")
        workflow.add_node("match_roles", self.match_to_existing_roles_node)
        workflow.add_node("generate_diff", self.generate_diff_node)
        workflow.add_node("human_review", self.human_review_node)
        workflow.add_node("save_data", self.save_approved_data_node)
        workflow.add_node("end_workflow", self.end_workflow_node)

        workflow.add_edge("extract_information", "match_roles")
        workflow.add_edge("match_roles", "generate_diff")
        workflow.add_edge("generate_diff", "human_review")

        workflow.add_conditional_edges(
            "human_review",
            self.decide_after_review,
            {
                "save_data": "save_data",
                "end_workflow": "end_workflow",
                END: END
            }
        )
        workflow.add_edge("save_data", "end_workflow")
        workflow.add_edge("end_workflow", END)


        self.graph = workflow.compile()

    async def _call_mcp_tool(
        self,
        mcp_client: MultiServerMCPClient, # Pass client explicitly
        server_name: str,
        tool_name: str,
        params: Dict[str, Any],
        is_security_gateway_call: bool = False # To prevent recursion for direct SG calls
    ) -> Any:
        """
        Helper method to call an MCP tool, potentially via the Security Gateway.
        """
        print(f"Workflow: Attempting MCP call: Server='{server_name}', Tool='{tool_name}'")

        # 1. Call Security Gateway for validation (unless this call IS to the security gateway)
        if not is_security_gateway_call and self.mcp_config.get("security_gateway"):
            try:
                validation_params = {
                    "target_server": server_name,
                    "method": tool_name,
                    "params": params
                }
                print(f"Workflow: Calling Security Gateway for validation of '{server_name}.{tool_name}'.")
                validation_result = await mcp_client.call_tool(
                    "security_gateway",
                    "validate_and_forward",
                    validation_params
                )
                # print(f"Workflow: Security Gateway validation result: {validation_result}")

                if isinstance(validation_result, dict) and validation_result.get("status") == "success":
                    # Use validated params if returned and structured that way
                    # params = validation_result.get("validated_params", params) # Assuming SG returns this structure
                    print(f"Workflow: Security Gateway validation SUCCESS for '{server_name}.{tool_name}'.")
                else:
                    error_detail = validation_result.get('error', validation_result.get('message', 'Unknown validation error from Security Gateway'))
                    print(f"Workflow: Security Gateway validation FAILED for '{server_name}.{tool_name}': {error_detail}")
                    # Return the error from SG so the node can handle it
                    return {"error": f"Security Gateway: {error_detail}", "status": "failure_security_validation"}

            except Exception as e:
                print(f"Workflow: Exception during Security Gateway call for {server_name}.{tool_name}: {e}")
                # Return an error structure that nodes can handle
                return {"error": f"Exception calling Security Gateway: {e}", "status": "failure_security_gateway_call"}

        # 2. Call the actual tool on the target server
        try:
            # print(f"Workflow: Calling actual tool: Server='{server_name}', Tool='{tool_name}', Params='{params}'")
            tool_response = await mcp_client.call_tool(server_name, tool_name, params)
            # print(f"Workflow: MCP tool '{server_name}.{tool_name}' response: {tool_response}")

            # Standardize error checking for tool responses
            if isinstance(tool_response, dict) and ("error" in tool_response or tool_response.get("status", "").startswith("failure")):
                error_msg = tool_response.get("error", tool_response.get("message", f"Unknown error from {server_name}.{tool_name}"))
                print(f"Workflow: MCP tool '{server_name}.{tool_name}' reported an error: {error_msg}")
            return tool_response
        except Exception as e:
            print(f"Workflow: Exception calling MCP tool '{server_name}.{tool_name}': {e}")
            # Return an error structure that nodes can handle
            return {"error": f"Exception calling {server_name}.{tool_name}: {e}", "status": f"failure_tool_exception"}
            raise

    async def start_workflow(self, state: ResumeProcessingState, config: Optional[Dict[str, Any]] = None) -> ResumeProcessingState: # Added config
        print("Workflow Node: start_workflow")

        # Carry over initial_input_data from the input state if not already set
        # The run method now populates initial_input_data in the very first state dictionary.
        if "initial_input_data" not in state:
            state["initial_input_data"] = {} # Should ideally be passed by run()

        # If it's a re-run for review, workflow_id and document_id should already be in the state.
        if not state.get("workflow_id"):
            state["workflow_id"] = str(uuid.uuid4())

        if not state.get("document_id"):
            if state.get("original_file_path"):
                state["document_id"] = "doc_" + str(uuid.uuid4()) # Use fresh UUID for doc id
            else:
                state["document_id"] = "doc_error_" + str(uuid.uuid4())
                state.get("error_log", []).append("Original file path was missing when creating document_id.")

        # Set initial status unless it's a specific re-run status like PENDING_REVIEW_PROCESSING
        if state.get("review_status") not in ["PENDING_REVIEW_PROCESSING"]:
            state["review_status"] = "INITIALIZED" # Changed from UNPROCESSED

        state["current_task_info"] = "Workflow initialized. Preparing for document classification."
        state["error_log"] = state.get("error_log", [])
        print(f"  State after start_workflow: WF_ID={state['workflow_id']}, DOC_ID={state['document_id']}, Status={state['review_status']}")
        return state

    async def classify_document_node(self, state: ResumeProcessingState, config: Optional[Dict[str, Any]] = None) -> ResumeProcessingState: # Added config
        mcp_client = config.get("mcp_client") if config else None
        if not mcp_client: raise ValueError("MCP Client not available in classify_document_node via config")

        print("Workflow Node: classify_document_node")
        state["current_task_info"] = "Classifying document and extracting text..."
        state["error_log"] = state.get("error_log", [])

        file_path = state.get("original_file_path")
        if not file_path:
            state["error_log"].append("Original file path is missing.")
            state["review_status"] = "ERROR"
            print("  Error: Original file path missing.")
            # TODO: Transition to an error state or END
            return state

        try:
            # The document_processor.extract_text tool also returns document_type
            # No separate classify_document MCP tool was exposed in document_processor.py
            # So, this node effectively does text extraction and gets type.
            # We'll use the 'document_type' string from the response and map to DocumentType enum.
            response = await self._call_mcp_tool(
                mcp_client,
                "document_processor",
                "extract_text",
                {"file_path": file_path}
            )

            if response and response.get("status") == "success":
                state["raw_content"] = response.get("extracted_text")
                doc_type_str = response.get("document_type") # e.g., "PDF"
                try:
                    state["document_type"] = DocumentType[doc_type_str] if doc_type_str else DocumentType.UNKNOWN
                except KeyError:
                    state["document_type"] = DocumentType.UNSUPPORTED
                    state["error_log"].append(f"Unknown document type string received: {doc_type_str}")
                print(f"  Document classified as: {state['document_type']}. Raw content length: {len(state.get('raw_content', ''))}")
            else:
                error_msg = response.get("error", "Failed to extract text or classify document.")
                state["error_log"].append(error_msg)
                state["review_status"] = "ERROR"
                state["document_type"] = DocumentType.UNSUPPORTED # Mark as unsupported on error
                print(f"  Error during text extraction/classification: {error_msg}")

        except Exception as e:
            error_msg = f"Exception in classify_document_node: {e}"
            state["error_log"].append(error_msg)
            state["review_status"] = "ERROR"
            state["document_type"] = DocumentType.UNSUPPORTED
            print(f"  Exception in classify_document_node: {error_msg}")
            # TODO: Add conditional edge to handle this error state if needed
        return state

    async def extract_information_node(self, state: ResumeProcessingState, config: Optional[Dict[str, Any]] = None) -> ResumeProcessingState:
        mcp_client = config.get("mcp_client") if config else self._temp_mcp_client
        if not mcp_client: raise ValueError("MCP Client not available in extract_information_node via config")

        print("Workflow Node: extract_information_node")
        state["current_task_info"] = "Extracting structured information..."
        state["error_log"] = state.get("error_log", [])

        doc_type = state.get("document_type")
        if not doc_type or doc_type in [DocumentType.UNSUPPORTED, DocumentType.UNKNOWN]:
            state["error_log"].append(f"Doc type {doc_type.name if doc_type else 'None'} is unsupported or unknown. Skipping LLM extraction.")
            # Not necessarily an error for the whole workflow, could be an expected outcome.
            # Depending on desired flow, might go to END or a specific handling node.
            state["review_status"] = "EXTRACTION_SKIPPED_UNSUPPORTED_TYPE"
            return state # Proceed to next step, which might be END or a human review of raw text.

        if not state.get("raw_content"):
            state["error_log"].append("Raw content missing, cannot extract information.")
            state["review_status"] = "ERROR" # This is more likely a workflow error.
            return state

        try:
            response: Optional[ExtractedData] = await self._call_mcp_tool(
                mcp_client, "document_processor", "process_resume",
                {"document_path": state["original_file_path"], "client_id": state.get("client_id")}
            )

            if response and isinstance(response, dict): # Ensure response is a dict
                if response.get("status") == "failure_security_validation" or response.get("status") == "failure_security_gateway_call":
                    error_msg = response.get("error", "Security validation failed for process_resume.")
                    state["error_log"].append(error_msg)
                    state["review_status"] = "ERROR_SECURITY"
                    return state
                if "error" in response or response.get("status", "").startswith("failure"): # Check for tool-specific errors
                    error_msg = response.get("error", "Unknown error from process_resume tool.")
                    state["error_log"].append(error_msg)
                    state["review_status"] = "ERROR_LLM_EXTRACTION"
                    # Fallback: keep raw_content, but no structured roles
                    state["extracted_roles"] = []
                    return state

                state["extracted_roles"] = response.get("professional_history", [])
                current_confidence = state.get("confidence_scores", {})
                if response.get("confidence_score") is not None:
                    current_confidence["llm_extraction_overall"] = response["confidence_score"]
                state["confidence_scores"] = current_confidence

                if response.get("errors"): # LLM-specific errors list
                    state["error_log"].extend(response["errors"])
                    print(f"  LLM extraction reported errors: {response['errors']}")

                print(f"  Successfully extracted {len(state.get('extracted_roles', []))} roles.")
                state["review_status"] = "EXTRACTION_COMPLETED"
            else:
                state["error_log"].append(f"Invalid or no response from process_resume tool: {response}")
                state["review_status"] = "ERROR_LLM_EXTRACTION"
                state["extracted_roles"] = []
                print(f"  Error: Invalid or no response from process_resume: {response}")

        except Exception as e:
            error_msg = f"Exception in extract_information_node: {e}"
            state["error_log"].append(error_msg)
            state["review_status"] = "ERROR" # General exception means a workflow/system error
            print(f"  Exception: {error_msg}")

        return state

    async def match_to_existing_roles_node(self, state: ResumeProcessingState, config: Optional[Dict[str, Any]] = None) -> ResumeProcessingState:
        mcp_client = config.get("mcp_client") if config else self._temp_mcp_client
        if not mcp_client: raise ValueError("MCP Client not available in match_to_existing_roles_node via config")

        print("Workflow Node: match_to_existing_roles_node")
        state["current_task_info"] = "Matching roles to existing Notion entries..."
        state["error_log"] = state.get("error_log", [])
        state["matched_pairs"] = [] # Ensure initialized
        state["new_roles"] = []     # Ensure initialized

        if not state.get("extracted_roles"): # Check if list is empty or None
            print("  No extracted roles to match. Skipping matching.")
            state["review_status"] = "MATCHING_SKIPPED_NO_ROLES"
            return state

        try:
            notion_response = await self._call_mcp_tool(
                mcp_client, "notion_integration", "query_existing_roles", {"client_id": state.get("client_id")}
            )

            if notion_response and isinstance(notion_response, dict) and notion_response.get("status") == "success":
                state["existing_roles"] = notion_response.get("roles", [])
                print(f"  Successfully queried {len(state.get('existing_roles', []))} existing roles from Notion.")
            else:
                error_msg = notion_response.get("error", "Failed to query existing roles from Notion.")
                state["error_log"].append(error_msg)
                state["review_status"] = "ERROR_NOTION_QUERY"
                print(f"  Error: {error_msg}. Proceeding without existing roles (all extracted will be new).")
                state["existing_roles"] = []

            extracted_roles = state.get("extracted_roles", [])
            existing_roles_notion = state.get("existing_roles", [])
            matched_existing_ids = set()

            for extr_role in extracted_roles:
                extr_company = str(extr_role.get("company", "")).strip().lower()
                extr_title = str(extr_role.get("title", "")).strip().lower()
                found_match = False
                for exist_role in existing_roles_notion:
                    exist_id = exist_role.get("notion_page_id")
                    if exist_id in matched_existing_ids: continue
                    exist_company = str(exist_role.get("company", "")).strip().lower()
                    exist_title = str(exist_role.get("title", "")).strip().lower()
                    if extr_company and extr_title and extr_company == exist_company and extr_title == exist_title:
                        state["matched_pairs"].append({
                            "extracted": extr_role, "existing": exist_role, "match_score": 0.95
                        })
                        matched_existing_ids.add(exist_id)
                        found_match = True
                        print(f"  Matched: Extracted '{extr_company} - {extr_title}' with Existing ID '{exist_id}'")
                        break
                if not found_match:
                    state["new_roles"].append(extr_role)
                    print(f"  New Role: Extracted '{extr_company} - {extr_title}' (no match found)")

            state["review_status"] = "MATCHING_COMPLETED"
            print(f"  Matching completed: {len(state.get('matched_pairs',[]))} pairs, {len(state.get('new_roles',[]))} new roles.")
        except Exception as e:
            error_msg = f"Exception in match_to_existing_roles_node: {e}"
            state["error_log"].append(error_msg)
            state["review_status"] = "ERROR_MATCHING"
            print(f"  Exception: {error_msg}")
        return state

    async def generate_diff_node(self, state: ResumeProcessingState, config: Optional[Dict[str, Any]] = None) -> ResumeProcessingState:
        print("Workflow Node: generate_diff_node")
        state["current_task_info"] = "Generating comparison for human review..."
        state["error_log"] = state.get("error_log", [])
        proposed_changes_list = []

        # Process new roles
        for new_role_data in state.get("new_roles", []):
            proposed_changes_list.append(
                {'type': 'NEW_ROLE', 'data': new_role_data}
            )
            print(f"  Proposing NEW_ROLE: {new_role_data.get('company')} - {new_role_data.get('title')}")

        # Process matched roles (for MVP, just list them side-by-side, no complex diff yet)
        for matched_pair in state.get("matched_pairs", []):
            # TODO: Implement actual diffing logic if needed.
            # For now, just presenting both for review.
            computed_diff = "No detailed diff generated for MVP. Review side-by-side."
            proposed_changes_list.append(
                {
                    'type': 'MATCHED_ROLE',
                    'extracted_data': matched_pair.get('extracted'),
                    'existing_data': matched_pair.get('existing'),
                    'diff': computed_diff
                }
            )
            print(f"  Proposing MATCHED_ROLE: {matched_pair.get('extracted',{}).get('company')} - {matched_pair.get('existing',{}).get('company')}")

        state['proposed_changes'] = proposed_changes_list
        if not proposed_changes_list:
            state["current_task_info"] = "No new or matched roles to review."
            state['review_status'] = "REVIEW_NOT_NEEDED" # Or a status that leads to end_workflow
        else:
            state['review_status'] = "PENDING_REVIEW"

        print(f"  Generated {len(proposed_changes_list)} items for review.")
        return state

    async def human_review_node(self, state: ResumeProcessingState, config: Optional[Dict[str, Any]] = None) -> ResumeProcessingState:
        print("Workflow Node: human_review_node (Simulated)")
        state["current_task_info"] = "Awaiting human review (simulated)..."
        state["error_log"] = state.get("error_log", [])

        # Simulate review outcome based on initial input or default
        simulated_outcome = state.get("initial_input_data", {}).get("simulated_review_outcome", "APPROVE_ALL_NEW")
        print(f"  Simulated review outcome: {simulated_outcome}")

        state['approved_changes'] = []
        state['rejected_changes'] = []

        proposed_changes = state.get("proposed_changes", [])
        if not proposed_changes:
            state["review_status"] = "REVIEW_SKIPPED_NO_PROPOSALS"
            print("  No proposed changes to review.")
            return state

        if simulated_outcome == "APPROVE_ALL":
            state['approved_changes'] = list(proposed_changes) # Approve everything
            state['review_status'] = "APPROVED"
            print(f"  Simulated: Approved all {len(state['approved_changes'])} proposed changes.")
        elif simulated_outcome == "APPROVE_ALL_NEW":
            for change in proposed_changes:
                if change.get('type') == 'NEW_ROLE':
                    state['approved_changes'].append(change)
            state['review_status'] = "APPROVED" # Could be PARTIALLY_APPROVED if some matches were not handled
            print(f"  Simulated: Approved {len(state['approved_changes'])} NEW_ROLE items.")
        elif simulated_outcome == "REJECT_ALL":
            state['rejected_changes'] = list(proposed_changes)
            state['review_status'] = "REJECTED"
            print(f"  Simulated: Rejected all {len(state['rejected_changes'])} proposed changes.")
        else: # Default or unknown simulation
            state["error_log"].append(f"Unknown simulated_review_outcome: {simulated_outcome}. Defaulting to no changes approved.")
            state['review_status'] = "REVIEW_ERROR_UNKNOWN_OUTCOME"
            print(f"  Warning: Unknown simulated outcome '{simulated_outcome}'. No changes approved.")

        return state

    def decide_after_review(self, state: ResumeProcessingState) -> str:
        print("Workflow Node: decide_after_review")
        review_status = state.get('review_status', "UNKNOWN")

        if review_status == "APPROVED":
            if state.get('approved_changes'): # Check if there's anything to save
                print("  Decision: Review approved, changes pending. Proceeding to save_data.")
                return "save_data"
            else:
                print("  Decision: Review approved, but no changes to save. Proceeding to end_workflow.")
                return "end_workflow"
        elif review_status == "REJECTED":
            print("  Decision: Review rejected. Proceeding to end_workflow.")
            return "end_workflow"
        elif review_status in ["REVIEW_SKIPPED_NO_PROPOSALS", "REVIEW_NOT_NEEDED"]:
            print(f"  Decision: Review skipped ({review_status}). Proceeding to end_workflow.")
            return "end_workflow"
        else: # Includes ERROR statuses from review, or unknown.
            print(f"  Decision: Review status is '{review_status}'. Proceeding to end_workflow (error or undefined path).")
            # Log this as it might indicate an issue if status was expected to be clear.
            state.get("error_log", []).append(f"Unexpected review status in decide_after_review: {review_status}")
            return "end_workflow" # Default to ending if status is not explicitly handled for continuation

    async def end_workflow_node(self, state: ResumeProcessingState, config: Optional[Dict[str, Any]] = None) -> ResumeProcessingState:
        print("Workflow Node: end_workflow_node")
        final_status = state.get('review_status', 'UNKNOWN_FINAL_STATUS')
        if "ERROR" in final_status:
             state["current_task_info"] = f"Workflow finished with errors. Final Status: {final_status}"
        elif final_status == "SAVE_COMPLETED":
             state["current_task_info"] = "Workflow finished successfully. Data saved."
        elif final_status == "SAVE_COMPLETED_WITH_ERRORS":
             state["current_task_info"] = "Workflow finished. Some data saved, but errors occurred."
        elif final_status in ["REJECTED", "REVIEW_SKIPPED_NO_PROPOSALS", "REVIEW_NOT_NEEDED", "APPROVED"]: # Approved but nothing to save
             state["current_task_info"] = f"Workflow finished. Final Status: {final_status}. No data saved to Notion."
        else:
             state["current_task_info"] = f"Workflow finished. Final Status: {final_status}."

        print(f"  Final task info: {state['current_task_info']}")
        # Final logging or cleanup can happen here
        return state

    async def save_approved_data_node(self, state: ResumeProcessingState, config: Optional[Dict[str, Any]] = None) -> ResumeProcessingState:
        mcp_client = config.get("mcp_client") if config else self._temp_mcp_client
        if not mcp_client: raise ValueError("MCP Client not available in save_approved_data_node via config")

        print("Workflow Node: save_approved_data_node")
        state["current_task_info"] = "Saving approved data to Notion and tracking citations..."
        state["error_log"] = state.get("error_log", [])

        # Operate on state['approved_changes']
        approved_items = state.get("approved_changes", [])
        roles_to_save = []
        for item in approved_items:
            if item.get('type') == 'NEW_ROLE':
                roles_to_save.append(item.get('data'))
            # TODO: Handle 'MATCHED_ROLE' with updates if diffing and update logic is implemented.
            # For MVP, only saving NEW_ROLE types.

        if not roles_to_save:
            print("  No new roles approved for saving. Skipping save actual.")
            state["review_status"] = state.get("review_status", "") + "_SAVE_SKIPPED_NO_APPROVED_NEW_ROLES" # Append to existing status
            state["current_task_info"] = "No new roles approved for saving."
            return state

        source_doc_fingerprint = state.get("document_id", "unknown_document_fingerprint")
        if source_doc_fingerprint == "unknown_document_fingerprint":
             state["error_log"].append("Document ID (fingerprint) is unknown for citation tracking.")

        saved_count = 0
        processed_roles_count = 0
        for role_data in roles_to_save:
            processed_roles_count +=1
            if not isinstance(role_data, dict): # Basic check
                state["error_log"].append(f"Skipping invalid role data item: {role_data}")
                continue
            try:
                print(f"  Attempting to save role: {role_data.get('company')} - {role_data.get('title')}")
                notion_add_response = await self._call_mcp_tool(
                    mcp_client, "notion_integration", "add_professional_role", {"role_data": dict(role_data)}
                )

                if notion_add_response and notion_add_response.get("status") == "success":
                    notion_page_id = notion_add_response.get("notion_page_id")
                    print(f"    Successfully saved role to Notion. Page ID: {notion_page_id}")
                    saved_count += 1

                    for achievement_text in role_data.get("achievements", []):
                        if not isinstance(achievement_text, str) or not achievement_text.strip(): continue
                        citation_payload = {
                            "source_document_fingerprint": source_doc_fingerprint,
                            "original_extracted_text": achievement_text,
                            "document_location": {
                                "document_id": state.get("document_id", "unknown_doc_id"),
                                "custom_location_info": f"Resume: {role_data.get('company')} - {role_data.get('title')}, Achievement"
                            },
                            "notion_page_id": notion_page_id,
                            "notion_field_name": "achievements"
                        }
                        citation_response = await self._call_mcp_tool(
                            mcp_client, "citation_tracker", "track_extraction", citation_payload
                        )
                        if not (citation_response and citation_response.get("status") == "success"):
                            error_msg = f"Citation fail for '{achievement_text[:30]}...': {citation_response.get('error', 'Unknown')}"
                            state["error_log"].append(error_msg)
                            print(f"    Error: {error_msg}")
                else:
                    error_msg = f"Notion save fail for '{role_data.get('company')}': {notion_add_response.get('error', 'Unknown')}"
                    state["error_log"].append(error_msg)
                    print(f"    Error: {error_msg}")
            except Exception as e:
                error_msg = f"Exception saving role '{role_data.get('company')}': {e}"
                state["error_log"].append(error_msg)
                print(f"    Exception: {error_msg}")

        # Update status based on how many of the approved roles were actually saved
        if saved_count == processed_roles_count and processed_roles_count > 0 :
             state["current_task_info"] = f"Successfully saved {saved_count} new roles to Notion and tracked citations."
             state["review_status"] = "SAVE_COMPLETED"
        elif saved_count > 0 and saved_count < processed_roles_count:
             state["current_task_info"] = f"Partially saved data: {saved_count}/{processed_roles_count} roles. Errors in log."
             state["review_status"] = "SAVE_COMPLETED_WITH_ERRORS"
        elif processed_roles_count > 0 and saved_count == 0: # Attempted to save but all failed
             state["current_task_info"] = f"Failed to save any of the {processed_roles_count} approved new roles. Errors in log."
             state["review_status"] = "SAVE_FAILED"
        else: # No roles were processed (e.g. approved_changes was empty or filtered to empty)
             state["current_task_info"] = "No new roles were processed for saving."
             # Keep previous review_status or set specific one like "SAVE_SKIPPED_NO_VALID_ROLES"
             if not state.get("review_status","").startswith("SAVE_"): # Avoid overwriting more specific skip status
                state["review_status"] = "SAVE_SKIPPED"


        return state


    async def run(self, input_data: Dict[str, Any]) -> ResumeProcessingState:
        """
        Runs the resume processing workflow with the given input.
        Input_data should contain 'original_file_path'. 'client_id' is optional.
        """
        print(f"Workflow Run: Starting with input: {input_data}")
        initial_state_dict = {
            "workflow_id": str(uuid.uuid4()),
            "original_file_path": input_data.get("original_file_path", ""),
            "client_id": input_data.get("client_id"),
            "document_id": "",
            "document_type": None,
            "raw_content": None,
            "extracted_roles": [],
            "existing_roles": [],
            "matched_pairs": [],
            "new_roles": [],
            "proposed_changes": [],
            "approved_changes": [],
            "rejected_changes": [],
            "citations_map": {},
            "review_status": "UNPROCESSED",
            "reviewer_notes": None,
            "confidence_scores": {},
            "processing_time_ms": None,
            "error_log": [],
            "current_task_info": "Initializing workflow..."
        }
        initial_state = ResumeProcessingState(**initial_state_dict)


        if not initial_state["original_file_path"]:
            initial_state["error_log"].append("Critical: original_file_path is required.")
            initial_state["review_status"] = "ERROR"
            print("Workflow Run: Critical error - original_file_path missing.")
            return initial_state

        start_time = datetime.now(timezone.utc)

        # Manage MCP client context per run
        async with MultiServerMCPClient(self.mcp_config) as mcp_client:
            # Bind the mcp_client to the node methods that need it for this invocation
            # LangGraph doesn't directly support passing extra args to nodes per invoke in compiled graph.
            # A common pattern is to use a callable class for nodes, or functools.partial.
            # For simplicity in this subtask, we'll adapt the methods to retrieve it if needed,
            # or consider if the client should be part of the state (not ideal).
            # The provided structure of StatefulGraph invokes methods with (state) or (state, config).
            #
            # Workaround: Pass mcp_client via the config object in `ainvoke`.
            # The 'config' parameter in `ainvoke` can be passed down to nodes.
            # Nodes need to be defined to accept `(self, state, config)`
            # For now, this subtask will assume `mcp_client` can be accessed if methods are adapted.
            # The solution below modifies node signatures to accept `config` and extracts `mcp_client` from it.

            # Modifying graph invocation to pass mcp_client via config
            # First, ensure nodes can accept config. Let's redefine nodes to accept config.
            # This requires graph definition to be dynamic or nodes to handle optional config.
            # For this subtask, we'll assume the _call_mcp_tool can somehow access a client.
            # A more robust way is to make nodes methods of a class that holds the client,
            # or pass client explicitly if graph structure allows.
            # The current structure with `self.graph.ainvoke(initial_state)` won't pass client easily.
            #
            # Let's adjust node methods to accept `config` and extract `mcp_client` from it.
            # This means `StatefulGraph` nodes should be called with `(state, config)`.
            # The graph compilation itself doesn't need to change for this if nodes are written to expect it.

            # The graph nodes should be defined as:
            # async def node_method(self, state: ResumeProcessingState, config: Optional[Dict[str, Any]] = None)
            # And then extract mcp_client from config.

            # Temporarily, for this subtask, let's assume `_call_mcp_tool` can get the client.
            # A proper solution would be to pass it through `config` in `ainvoke`.
            # For now, nodes will be modified to get mcp_client from config.

            invocation_config = {"mcp_client": mcp_client, "recursion_limit": 25}

            # Re-compiling graph with nodes that accept config (conceptual change for this step)
            # For this subtask, we can't recompile here easily.
            # The method _call_mcp_tool will need mcp_client passed to it.
            # Modifying nodes to use the passed mcp_client.

            # Hack: Temporarily set mcp_client on self for nodes to access. Not thread-safe / good for concurrent runs.
            self._temp_mcp_client = mcp_client

            final_state = await self.graph.ainvoke(initial_state, config=invocation_config)

            del self._temp_mcp_client # Clean up

        end_time = datetime.now(timezone.utc)
        processing_duration = (end_time - start_time).total_seconds() * 1000
        final_state["processing_time_ms"] = (final_state.get("processing_time_ms") or 0) + processing_duration

        print(f"Workflow Run: Finished. Final state (summary): ID={final_state['workflow_id']}, Status={final_state['review_status']}")
        if final_state['error_log']:
            print(f"  Errors encountered: {final_state['error_log']}")
        return final_state

    # Adjusting node signatures to accept config and extract mcp_client
    # This is a conceptual change for how nodes would be written.
    # For the actual execution with LangGraph, these methods will be wrapped or called
    # such that they receive the state and config.

    async def start_workflow(self, state: ResumeProcessingState, config: Optional[Dict[str, Any]] = None) -> ResumeProcessingState:
        # ... (same as before, does not need mcp_client)
        print("Workflow Node: start_workflow")
        if not state.get("workflow_id"):
            state["workflow_id"] = str(uuid.uuid4())
        if not state.get("document_id"):
            if state.get("original_file_path"):
                state["document_id"] = "doc_" + str(uuid.uuid5(uuid.NAMESPACE_DNS, state["original_file_path"]))
            else:
                state["document_id"] = "doc_" + str(uuid.uuid4())
        state["current_task_info"] = "Workflow started. Initializing..."
        state["error_log"] = state.get("error_log", [])
        state["review_status"] = "UNPROCESSED"
        return state

    async def classify_document_node(self, state: ResumeProcessingState, config: Optional[Dict[str, Any]] = None) -> ResumeProcessingState:
        mcp_client = config.get("mcp_client") if config else self._temp_mcp_client # Fallback for direct calls
        if not mcp_client: raise ValueError("MCP Client not available in classify_document_node via config")
        # ... (rest of the logic is same as before, using this mcp_client)
        print("Workflow Node: classify_document_node")
        state["current_task_info"] = "Classifying document and extracting text..."
        state["error_log"] = state.get("error_log", [])
        file_path = state.get("original_file_path")
        if not file_path:
            state["error_log"].append("Original file path is missing.")
            state["review_status"] = "ERROR"
            return state
        try:
            response = await self._call_mcp_tool(mcp_client, "document_processor", "extract_text", {"file_path": file_path})
            if response and response.get("status") == "success":
                state["raw_content"] = response.get("extracted_text")
                doc_type_str = response.get("document_type")
                try:
                    state["document_type"] = DocumentType[doc_type_str] if doc_type_str else DocumentType.UNKNOWN
                except KeyError:
                    state["document_type"] = DocumentType.UNSUPPORTED
                    state["error_log"].append(f"Unknown document type string: {doc_type_str}")
            else:
                error_msg = response.get("error", "Failed to extract text/classify.")
                state["error_log"].append(error_msg)
                state["review_status"] = "ERROR"
                state["document_type"] = DocumentType.UNSUPPORTED
        except Exception as e:
            error_msg = f"Exception in classify_document_node: {e}"
            state["error_log"].append(error_msg)
            state["review_status"] = "ERROR"
            state["document_type"] = DocumentType.UNSUPPORTED
        return state

    async def extract_information_node(self, state: ResumeProcessingState, config: Optional[Dict[str, Any]] = None) -> ResumeProcessingState:
        mcp_client = config.get("mcp_client") if config else self._temp_mcp_client
        if not mcp_client: raise ValueError("MCP Client not available in extract_information_node via config")
        # ... (rest of the logic is same as before, using this mcp_client)
        print("Workflow Node: extract_information_node")
        state["current_task_info"] = "Extracting structured information..."
        state["error_log"] = state.get("error_log", [])
        doc_type = state.get("document_type")
        if not doc_type or doc_type in [DocumentType.UNSUPPORTED, DocumentType.UNKNOWN]:
            state["error_log"].append(f"Doc type {doc_type.name if doc_type else 'None'} unsupported.")
            state["review_status"] = "ERROR"
            return state
        if not state.get("raw_content"):
            state["error_log"].append("Raw content missing for extraction.")
            state["review_status"] = "ERROR"
            return state
        try:
            response: Optional[ExtractedData] = await self._call_mcp_tool(
                mcp_client, "document_processor", "process_resume",
                {"document_path": state["original_file_path"], "client_id": state.get("client_id")}
            )
            if response:
                state["extracted_roles"] = response.get("professional_history", [])
                current_confidence = state.get("confidence_scores", {})
                if response.get("confidence_score") is not None:
                    current_confidence["llm_extraction_overall"] = response["confidence_score"]
                state["confidence_scores"] = current_confidence
                if response.get("errors"): state["error_log"].extend(response["errors"])
            else:
                state["error_log"].append("No response from process_resume.")
                state["review_status"] = "ERROR"
        except Exception as e:
            error_msg = f"Exception in extract_information_node: {e}"
            state["error_log"].append(error_msg)
            state["review_status"] = "ERROR"
        return state


async def main_test_run():
    """Main function to run workflow for testing."""
    # Create a dummy file for testing
    dummy_file_dir = "static/uploads"
    os.makedirs(dummy_file_dir, exist_ok=True)
    dummy_file_path = os.path.join(dummy_file_dir, "sample_resume.txt")
    with open(dummy_file_path, "w", encoding="utf-8") as f:
        f.write("John Doe - Software Engineer at Tech Corp (2020-Present). Developed cool apps.")

    workflow_instance = ResumeProcessingWorkflow()

    test_input_data = {
        "original_file_path": dummy_file_path,
        "client_id": "test_client_001"
    }

    print(f"Starting workflow test with input: {test_input_data}")
    final_state = await workflow_instance.run(test_input_data)

    print("\n--- Final Workflow State ---")
    # Pretty print the final state
    final_state_str = json.dumps(final_state, default=lambda o: o.name if isinstance(o, DocumentType) else str(o), indent=2)
    print(final_state_str)

    # Clean up dummy file
    # os.remove(dummy_file_path)


if __name__ == "__main__":
    # Ensure resume_mcp_config.json exists for load_mcp_config()
    # If it's in the root, this should work if script is run from root or workflow dir.
    # A dummy config might be needed if real one isn't set up.
    if not os.path.exists("resume_mcp_config.json"):
        # Try path relative to this file's directory
        current_dir_path = os.path.dirname(os.path.abspath(__file__))
        rel_config = os.path.join(current_dir_path, "..", "resume_mcp_config.json")
        if not os.path.exists(rel_config):
             print("WARNING: resume_mcp_config.json not found in root or parent. Workflow may fail to load MCP config.")
             print("Creating a dummy resume_mcp_config.json for test purposes.")
             dummy_config_content = {
                "security_gateway": {"command": "echo", "args": ["dummy security gateway"], "transport": "stdio"},
                "document_processor": {"command": "echo", "args": ["dummy doc processor"], "transport": "stdio"}
                # Add other dummy server configs if needed by the workflow parts being tested
             }
             # Create dummy in parent if running from workflow dir
             config_to_create_path = rel_config if "workflow" in current_dir_path else "resume_mcp_config.json"
             try:
                with open(config_to_create_path, "w") as f_cfg:
                    json.dump(dummy_config_content, f_cfg, indent=2)
                print(f"Dummy config created at {os.path.abspath(config_to_create_path)}")
             except Exception as e_cfg_create:
                 print(f"Could not create dummy config: {e_cfg_create}")

    asyncio.run(main_test_run())
