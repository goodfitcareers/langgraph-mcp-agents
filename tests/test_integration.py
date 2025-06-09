import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
import os
import uuid

# Assuming workflow and state are importable
# from workflow.pipeline import ResumeProcessingWorkflow
# from workflow.state import ResumeProcessingState, DocumentType

# Placeholder definitions for this outline
class ResumeProcessingWorkflow:
    async def run(self, input_data): return {} # Mock run
class ResumeProcessingState(dict): pass
class DocumentType(Enum): PDF = "PDF"; DOCX = "DOCX"; TXT = "TXT"


# --- Notes on Integration Test Strategy ---
# - Integration tests will focus on the interactions between the workflow and MCP servers.
# - MCP servers themselves will be mocked at the client call level.
#   This means we are not testing the MCP server's internal logic here (that's for their own unit tests),
#   but rather that the workflow correctly calls them and handles their responses.
# - We need a way to inject mock responses for each MCP call the workflow makes.
#   This can be done by mocking `MultiServerMCPClient.call_tool` or a similar method
#   that the workflow's `_call_mcp_tool` uses.
# - Test data (dummy file paths) will be used, but the content of the files might be
#   less important if the parser outputs are directly mocked.
# - The state evolution through the graph will be a key assertion point.

TEST_DATA_DIR_INTEGRATION = os.path.join(os.path.dirname(__file__), "test_data")
# Ensure TEST_DATA_DIR_INTEGRATION / "dummy_resume.pdf" etc. exist or are mocked appropriately.

class TestResumeWorkflowIntegration(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        """Setup common resources for integration tests."""
        # It might be useful to have a helper that creates a default initial state
        # or a ResumeProcessingWorkflow instance here.
        self.workflow_runner = ResumeProcessingWorkflow() # Assuming it can be instantiated

        # Create dummy files if they don't exist, or ensure mocks handle file access.
        os.makedirs(TEST_DATA_DIR_INTEGRATION, exist_ok=True)
        with open(os.path.join(TEST_DATA_DIR_INTEGRATION, "dummy_integration.pdf"), "w") as f:
            f.write("dummy pdf content for integration test")
        with open(os.path.join(TEST_DATA_DIR_INTEGRATION, "dummy_integration.docx"), "w") as f:
            f.write("dummy docx content for integration test")
        with open(os.path.join(TEST_DATA_DIR_INTEGRATION, "dummy_integration.txt"), "w") as f:
            f.write("dummy txt content for integration test")


    @patch('langchain_mcp_adapters.client.MultiServerMCPClient.call_tool', new_callable=AsyncMock)
    async def test_e2e_pdf_new_role_approved(self, mock_mcp_call_tool):
        """
        Test end-to-end flow for a new PDF resume, where a new role is extracted and approved.
        """
        # --- Mock MCP Server Responses ---
        # This requires knowing the sequence of calls the workflow will make.

        # 1. Security Gateway (called by _call_mcp_tool before each actual tool call)
        #    - For document_processor.extract_text
        #    - For document_processor.process_resume
        #    - For notion_integration.query_existing_roles
        #    - For notion_integration.add_professional_role
        #    - For citation_tracker.track_extraction
        #    For simplicity, assume SG always returns success for this test path,
        #    or mock specific SG responses if its logic is part of what's tested.
        #    If SG is complex, mock it to return {"status": "success", "validated_params": params}.

        mock_mcp_responses = []

        # Expected call to security_gateway for extract_text
        mock_mcp_responses.append({"status": "success", "validated_params": {}})
        # Expected call to document_processor.extract_text
        mock_mcp_responses.append({
            "status": "success",
            "extracted_text": "John Doe. Engineer at NewCo (2023-Present). Did stuff.",
            "document_type": "PDF" # Assuming string representation from the tool
        })

        # Expected call to security_gateway for process_resume
        mock_mcp_responses.append({"status": "success", "validated_params": {}})
        # Expected call to document_processor.process_resume
        mock_mcp_responses.append({
            "status": "success", # Assuming process_resume returns status now
            "professional_history": [{
                "company": "NewCo", "title": "Engineer",
                "start_year": 2023, "end_year": "Present",
                "achievements": ["Did stuff."]
            }],
            "confidence_score": 0.9,
            "errors": []
        })

        # Expected call to security_gateway for query_existing_roles
        mock_mcp_responses.append({"status": "success", "validated_params": {}})
        # Expected call to notion_integration.query_existing_roles
        mock_mcp_responses.append({"status": "success", "roles": []}) # No existing roles

        # Human review is simulated via input_data for this test
        # So, next calls are for saving data

        # Expected call to security_gateway for add_professional_role
        mock_mcp_responses.append({"status": "success", "validated_params": {}})
        # Expected call to notion_integration.add_professional_role
        mock_mcp_responses.append({"status": "success", "notion_page_id": "page_newco_engineer"})

        # Expected call to security_gateway for track_extraction (for each achievement)
        mock_mcp_responses.append({"status": "success", "validated_params": {}})
        # Expected call to citation_tracker.track_extraction
        mock_mcp_responses.append({"status": "success", "citation_id": str(uuid.uuid4())})

        mock_mcp_call_tool.side_effect = mock_mcp_responses

        # --- Prepare Input Data ---
        input_data = {
            "original_file_path": os.path.join(TEST_DATA_DIR_INTEGRATION, "dummy_integration.pdf"),
            "client_id": "e2e_client_1",
            "simulated_review_outcome": "REVIEW_APPROVED_NEW" # To approve the new role
        }

        # --- Run Workflow ---
        # final_state = await self.workflow_runner.run(input_data)

        # --- Assertions ---
        # self.assertIsInstance(final_state, ResumeProcessingState)
        # self.assertEqual(final_state.get("review_status"), "SAVE_COMPLETED") # Or whatever the final status is
        # self.assertFalse(final_state.get("error_log"), f"Workflow had errors: {final_state.get('error_log')}")

        # # Check if Notion add_professional_role was called correctly (via mock calls)
        # # The 5th actual tool call (after 2 SG, 2 DP, 1 SG, 1 NotionQuery, 1 SG)
        # notion_add_call = next((c for c in mock_mcp_call_tool.call_args_list if c.args[1] == "notion_integration" and c.args[2] == "add_professional_role"), None)
        # self.assertIsNotNone(notion_add_call, "add_professional_role was not called on Notion server")
        # self.assertEqual(notion_add_call.args[3]["role_data"]["company"], "NewCo")

        # # Check if citation tracker was called
        # citation_call = next((c for c in mock_mcp_call_tool.call_args_list if c.args[1] == "citation_tracker" and c.args[2] == "track_extraction"), None)
        # self.assertIsNotNone(citation_call, "track_extraction was not called")
        # self.assertEqual(citation_call.args[3]["notion_page_id"], "page_newco_engineer")
        # self.assertEqual(citation_call.args[3]["original_extracted_text"], "Did stuff.")
        self.skipTest("E2E test needs careful mock orchestration and workflow instance.")


    @patch('langchain_mcp_adapters.client.MultiServerMCPClient.call_tool', new_callable=AsyncMock)
    async def test_e2e_docx_matched_role_no_changes_needed(self, mock_mcp_call_tool):
        """
        Test flow where a DOCX resume provides data that matches an existing Notion entry,
        and no changes are needed.
        """
        # --- Mock MCP Server Responses ---
        mock_mcp_responses = []
        # SG for extract_text
        mock_mcp_responses.append({"status": "success", "validated_params": {}})
        # document_processor.extract_text
        mock_mcp_responses.append({
            "status": "success",
            "extracted_text": "Jane Smith. Senior PM at OldCorp (2020-2022). Managed products.",
            "document_type": "DOCX"
        })
        # SG for process_resume
        mock_mcp_responses.append({"status": "success", "validated_params": {}})
        # document_processor.process_resume
        extracted_role_data = {
            "company": "OldCorp", "title": "Senior PM", "start_year": 2020, "end_year": 2022,
            "achievements": ["Managed products."]
        }
        mock_mcp_responses.append({
            "status": "success",
            "professional_history": [extracted_role_data],
            "confidence_score": 0.95, "errors": []
        })
        # SG for query_existing_roles
        mock_mcp_responses.append({"status": "success", "validated_params": {}})
        # notion_integration.query_existing_roles (return one matching role)
        existing_role_data = {
            "notion_page_id": "page_oldcorp_srpm",
            **extracted_role_data # Assume it's identical for "no changes needed"
        }
        mock_mcp_responses.append({"status": "success", "roles": [existing_role_data]})

        mock_mcp_call_tool.side_effect = mock_mcp_responses

        # --- Prepare Input Data ---
        input_data = {
            "original_file_path": os.path.join(TEST_DATA_DIR_INTEGRATION, "dummy_integration.docx"),
            "client_id": "e2e_client_2",
            # No simulated_review_outcome needed if it goes to REVIEW_NOT_NEEDED
        }

        # --- Run Workflow ---
        # final_state = await self.workflow_runner.run(input_data)

        # --- Assertions ---
        # self.assertEqual(final_state.get("review_status"), "REVIEW_NOT_NEEDED") # Or a similar status
        # self.assertTrue(len(final_state.get("matched_pairs", [])) == 1)
        # self.assertTrue(len(final_state.get("new_roles", [])) == 0)
        # self.assertFalse(final_state.get("error_log"))
        self.skipTest("E2E test for matched role needs mock orchestration.")


    @patch('langchain_mcp_adapters.client.MultiServerMCPClient.call_tool', new_callable=AsyncMock)
    async def test_e2e_txt_extraction_error(self, mock_mcp_call_tool):
        """Test flow where text extraction from a TXT file fails."""
        # --- Mock MCP Server Responses ---
        # SG for extract_text
        mock_mcp_responses = [{"status": "success", "validated_params": {}}]
        # document_processor.extract_text returns an error
        mock_mcp_responses.append({
            "status": "failure",
            "error": "Failed to parse TXT file due to encoding issue."
        })
        mock_mcp_call_tool.side_effect = mock_mcp_responses

        # --- Prepare Input Data ---
        input_data = {
            "original_file_path": os.path.join(TEST_DATA_DIR_INTEGRATION, "dummy_integration.txt"),
            "client_id": "e2e_client_3"
        }

        # --- Run Workflow ---
        # final_state = await self.workflow_runner.run(input_data)

        # --- Assertions ---
        # self.assertIn("ERROR", final_state.get("review_status", "")) # e.g. ERROR_TEXT_EXTRACTION
        # self.assertTrue(final_state.get("error_log"))
        # self.assertIn("Failed to parse TXT file", final_state.get("error_log")[0])
        self.skipTest("E2E test for extraction error needs mock orchestration.")

    @patch('langchain_mcp_adapters.client.MultiServerMCPClient.call_tool', new_callable=AsyncMock)
    async def test_e2e_security_gateway_rejects_file(self, mock_mcp_call_tool):
        """Test flow where Security Gateway rejects the file before Document Processor is called."""
        # --- Mock MCP Server Responses ---
        # Security Gateway for extract_text rejects the call
        mock_mcp_call_tool.return_value = { # Only one call expected
            "status": "failure_security_validation",
            "error": "Security Gateway: File type .exe not allowed."
        }

        # --- Prepare Input Data ---
        input_data = {
            "original_file_path": "dangerous_file.exe", # Path doesn't need to exist for this mock
            "client_id": "e2e_client_4"
        }

        # --- Run Workflow ---
        # final_state = await self.workflow_runner.run(input_data)

        # --- Assertions ---
        # # The workflow should ideally stop early. The error might appear in classify_document_node.
        # self.assertIn("ERROR_SECURITY", final_state.get("review_status", ""))
        # self.assertTrue(final_state.get("error_log"))
        # self.assertIn("Security Gateway: File type .exe not allowed.", final_state.get("error_log")[0])
        # # Check that subsequent MCP calls (like process_resume) were NOT made.
        # # This means mock_mcp_call_tool should have been called only once (for the SG validation of extract_text)
        # self.assertEqual(mock_mcp_call_tool.call_count, 1) # If SG is called for every tool, this might be 1
        self.skipTest("E2E test for Security Gateway rejection needs mock orchestration.")


if __name__ == '__main__':
    unittest.main()
