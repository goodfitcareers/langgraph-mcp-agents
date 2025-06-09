from typing import TypedDict, List, Dict, Optional, Any, Union
from enum import Enum

# --- Supporting Enum Definitions ---

class DocumentType(Enum):
    """Type of the document being processed."""
    PDF = "application/pdf"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    DOC = "application/msword" # Older .doc format
    TEXT = "text/plain"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown" # If type cannot be determined initially

# --- Professional History (Simplified for state, full definition in document_processor) ---
# For the workflow state, we might not need the full strictness of the ProfessionalHistory
# TypedDict from the MCP server if it's complex to share directly, or we can redefine it.
# For now, let's use Dict[str, Any] as a placeholder for ProfessionalHistory items
# in lists like extracted_roles, new_roles, etc.
# A more robust solution would be to have a shared types library.

# Example of what a ProfessionalHistory item might look like (for context):
# class ProfessionalHistory(TypedDict, total=False):
#     company: str
#     title: str
#     start_year: Optional[int]
#     end_year: Optional[Union[int, str]] # Can be "Present" or an int
#     manager_title: Optional[str]
#     direct_reports: Optional[int]
#     budget_responsibility: Optional[str]
#     headcount: Optional[int]
#     quota: Optional[str]
#     peer_functions: Optional[List[str]]
#     achievements: List[str]
#     responsibilities: List[str]
#     # From NotionIntegration schema:
#     notion_page_id: Optional[str]
#     sources: Optional[List[Dict[str, str]]]
#     confidence_score: Optional[float]
#     last_updated: Optional[str]


# --- Main State Definition ---

class ResumeProcessingState(TypedDict):
    """
    Represents the state of the resume processing workflow in LangGraph.
    It holds all data related to a single resume processing instance,
    from initial upload through extraction, review, and finalization.
    """
    workflow_id: str  # Unique identifier for this workflow instance
    client_id: Optional[str]  # Identifier for the client/user initiating the process

    # Document related fields
    document_id: str  # Unique identifier for the document being processed
    original_file_path: str  # Path to the originally uploaded file
    document_type: Optional[DocumentType] # Enum representing the detected document type
    raw_content: Optional[str]  # Raw text extracted from the document

    # Extraction and Matching
    # Using Dict[str, Any] for ProfessionalHistory for now to simplify type sharing.
    # In a mature system, ProfessionalHistory would be a shared type.
    extracted_roles: Optional[List[Dict[str, Any]]]  # Roles extracted by the DocumentProcessor
    existing_roles: Optional[List[Dict[str, Any]]]  # Roles existing in Notion (or other DB)

    # Matching and Diffing (more detailed structures might be needed for these)
    matched_pairs: Optional[List[Dict[str, Any]]]
    # Example for matched_pairs: [{'extracted': extracted_role_dict, 'existing': existing_role_dict, 'match_score': 0.9}]

    new_roles: Optional[List[Dict[str, Any]]] # Extracted roles identified as new

    # Proposed changes (e.g., diffs or specific instructions for updates)
    # Could be a list of operations: {'op': 'add', 'path': '/roles/1/achievements', 'value': 'New achievement'}
    # Or simpler: {'role_id_to_update': 'xyz', 'field_to_change': 'title', 'new_value': 'Senior PM'}
    proposed_changes: Optional[List[Dict[str, Any]]]

    # Review and Approval
    approved_changes: Optional[List[Dict[str, Any]]] # Changes approved by the user
    rejected_changes: Optional[List[Dict[str, Any]]] # Changes rejected by the user

    review_status: Optional[str]
    # Examples: "UNPROCESSED", "PENDING_SECURITY_VALIDATION", "PENDING_TEXT_EXTRACTION",
    # "PENDING_LLM_EXTRACTION", "PENDING_NOTION_QUERY", "PENDING_MATCHING",
    # "PENDING_REVIEW", "REVIEW_COMPLETED_APPROVED", "REVIEW_COMPLETED_REJECTED",
    # "PROCESSING_UPDATES", "COMPLETED", "ERROR"

    reviewer_notes: Optional[str] # Notes from the human reviewer

    # Citations and Confidence
    # citations_map could map a unique ID of an extracted item (e.g., role hash, or specific achievement hash)
    # to a list of citation objects.
    citations_map: Optional[Dict[str, List[Dict[str, Any]]]]
    # Example: {"role_company_TechCorp_title_SWE": [citation_obj1, citation_obj2]}

    confidence_scores: Optional[Dict[str, float]]
    # Example: {"overall_extraction": 0.85, "role_TechCorp_SWE_achievements": 0.92}

    # Workflow Metadata
    processing_time_ms: Optional[float] # Total time taken for processing steps
    error_log: Optional[List[str]] # List of error messages encountered
    current_task_info: Optional[str] # User-friendly message about the current step (e.g., "Extracting text from PDF...")

    # Ensure all fields that can be None are marked as Optional.
    # This is implicitly handled by TypedDict if a field is not listed,
    # but explicit Optional makes it clearer.
    # For total=False in TypedDict, all fields are optional by default.
    # However, the problem description implies some fields are mandatory (like workflow_id).
    # Sticking to TypedDict's default (total=True unless specified) means non-Optional fields are required.
    # The current definition uses Optional where appropriate.

# Example usage (for illustration, not part of the file content):
# if __name__ == "__main__":
#     initial_state = ResumeProcessingState(
#         workflow_id="wf_123",
#         document_id="doc_abc",
#         original_file_path="/path/to/resume.pdf",
#         # All other fields would be None or their default initially
#         client_id=None,
#         document_type=None,
#         raw_content=None,
#         extracted_roles=None,
#         existing_roles=None,
#         matched_pairs=None,
#         new_roles=None,
#         proposed_changes=None,
#         approved_changes=None,
#         rejected_changes=None,
#         citations_map=None,
#         review_status="UNPROCESSED",
#         reviewer_notes=None,
#         confidence_scores=None,
#         processing_time_ms=None,
#         error_log=[],
#         current_task_info="Workflow initiated."
#     )
#     print(initial_state)
