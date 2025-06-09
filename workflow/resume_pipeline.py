"""
Resume Processing Pipeline - LangGraph Workflow
Orchestrates the complete resume automation workflow using MCP servers
"""

import os
import uuid
import logging
from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime

from langgraph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResumeProcessingState(TypedDict):
    """State schema for the resume processing workflow."""
    
    # Workflow identifiers
    workflow_id: str
    client_name: str
    document_id: str
    
    # File processing state
    document_path: str
    document_type: str
    file_size: int
    secure_path: str
    
    # Processing state
    raw_text: str
    extracted_roles: List[Dict[str, Any]]
    existing_roles: List[Dict[str, Any]]
    
    # Matching and changes
    matched_pairs: List[Dict[str, Any]]
    new_roles: List[Dict[str, Any]]
    proposed_changes: List[Dict[str, Any]]
    
    # Human review
    review_status: str  # "pending", "approved", "rejected", "editing"
    approved_changes: List[Dict[str, Any]]
    reviewer_notes: str
    
    # Citations and metadata
    citations: Dict[str, Any]
    confidence_scores: Dict[str, float]
    processing_metadata: Dict[str, Any]
    
    # Error handling
    error_log: List[str]
    warnings: List[str]
    
    # Status tracking
    current_step: str
    completed_steps: List[str]
    total_processing_time: float

class ResumeProcessingWorkflow:
    """Main workflow class for resume processing."""
    
    def __init__(self):
        self.mcp_client = None
        self.workflow = None
        self._setup_mcp_servers()
        self._build_workflow()
    
    def _setup_mcp_servers(self):
        """Initialize MCP server connections."""
        
        self.mcp_config = {
            "security_gateway": {
                "command": "python",
                "args": ["mcp_servers/security_gateway.py"],
                "transport": "stdio"
            },
            "document_processor": {
                "command": "python", 
                "args": ["mcp_servers/document_processor.py"],
                "transport": "stdio"
            },
            "notion_integration": {
                "command": "python",
                "args": ["mcp_servers/notion_integration.py"], 
                "transport": "stdio"
            }
        }
        
        logger.info("MCP server configuration initialized")
    
    async def _initialize_mcp_client(self):
        """Initialize the MCP client if not already done."""
        if not self.mcp_client:
            self.mcp_client = MultiServerMCPClient(self.mcp_config)
            await self.mcp_client.__aenter__()
            logger.info("MCP client initialized successfully")
    
    def _build_workflow(self):
        """Build the LangGraph workflow."""
        
        workflow = StateGraph(ResumeProcessingState)
        
        # Add workflow nodes
        workflow.add_node("validate_security", self.validate_document_security)
        workflow.add_node("extract_text", self.extract_document_text)
        workflow.add_node("extract_roles", self.extract_professional_roles)
        workflow.add_node("query_existing", self.query_existing_roles)
        workflow.add_node("match_roles", self.match_and_compare_roles)
        workflow.add_node("generate_diff", self.generate_changes_diff)
        workflow.add_node("human_review", self.human_review_interrupt)
        workflow.add_node("apply_changes", self.apply_approved_changes)
        workflow.add_node("finalize", self.finalize_processing)
        
        # Add workflow edges
        workflow.add_edge("validate_security", "extract_text")
        workflow.add_edge("extract_text", "extract_roles")
        workflow.add_edge("extract_roles", "query_existing")
        workflow.add_edge("query_existing", "match_roles")
        workflow.add_edge("match_roles", "generate_diff")
        workflow.add_edge("generate_diff", "human_review")
        workflow.add_edge("human_review", "apply_changes")
        workflow.add_edge("apply_changes", "finalize")
        
        # Set entry point
        workflow.set_entry_point("validate_security")
        
        # Add human review interrupt
        workflow.add_interrupt("human_review")
        
        # Compile with checkpoint manager for persistence
        self.workflow = workflow.compile(checkpointer=MemorySaver())
        
        logger.info("LangGraph workflow compiled successfully")
    
    async def validate_document_security(self, state: ResumeProcessingState) -> ResumeProcessingState:
        """Step 1: Validate document security using Security Gateway MCP."""
        
        state["current_step"] = "validate_security"
        state["processing_metadata"]["start_time"] = datetime.now().isoformat()
        
        try:
            await self._initialize_mcp_client()
            
            # Basic validation logic here
            # This would call the security gateway MCP server
            
            state["completed_steps"].append("validate_security")
            logger.info(f"Security validation completed for document {state.get('document_id', 'unknown')}")
            
        except Exception as e:
            state["error_log"].append(f"Security validation exception: {str(e)}")
            logger.error(f"Security validation failed: {e}")
        
        return state
    
    async def extract_document_text(self, state: ResumeProcessingState) -> ResumeProcessingState:
        """Step 2: Extract text from document using Document Processor MCP."""
        
        state["current_step"] = "extract_text"
        
        try:
            # Text extraction logic here
            # This would call the document processor MCP server
            
            state["completed_steps"].append("extract_text")
            logger.info(f"Text extraction completed")
            
        except Exception as e:
            state["error_log"].append(f"Text extraction exception: {str(e)}")
            logger.error(f"Text extraction failed: {e}")
        
        return state
    
    async def extract_professional_roles(self, state: ResumeProcessingState) -> ResumeProcessingState:
        """Step 3: Extract professional roles using Claude via Document Processor MCP."""
        
        state["current_step"] = "extract_roles"
        
        try:
            # Role extraction logic here
            # This would call Claude through the document processor MCP server
            
            state["completed_steps"].append("extract_roles")
            logger.info(f"Role extraction completed")
            
        except Exception as e:
            state["error_log"].append(f"Role extraction exception: {str(e)}")
            logger.error(f"Role extraction failed: {e}")
        
        return state
    
    async def query_existing_roles(self, state: ResumeProcessingState) -> ResumeProcessingState:
        """Step 4: Query existing roles from Notion database."""
        
        state["current_step"] = "query_existing"
        
        try:
            # Query existing roles logic here
            # This would call the Notion integration MCP server
            
            state["completed_steps"].append("query_existing")
            logger.info(f"Existing roles queried")
            
        except Exception as e:
            state["error_log"].append(f"Existing roles query exception: {str(e)}")
            logger.error(f"Existing roles query failed: {e}")
        
        return state
    
    async def match_and_compare_roles(self, state: ResumeProcessingState) -> ResumeProcessingState:
        """Step 5: Match extracted roles with existing roles."""
        
        state["current_step"] = "match_roles"
        
        try:
            # Role matching logic here
            
            state["completed_steps"].append("match_roles")
            logger.info(f"Role matching completed")
            
        except Exception as e:
            state["error_log"].append(f"Role matching exception: {str(e)}")
            logger.error(f"Role matching failed: {e}")
        
        return state
    
    async def generate_changes_diff(self, state: ResumeProcessingState) -> ResumeProcessingState:
        """Step 6: Generate human-readable diff of proposed changes."""
        
        state["current_step"] = "generate_diff"
        
        try:
            # Generate diff logic here
            state["review_status"] = "pending"
            
            state["completed_steps"].append("generate_diff")
            logger.info(f"Changes diff generated")
            
        except Exception as e:
            state["error_log"].append(f"Diff generation exception: {str(e)}")
            logger.error(f"Diff generation failed: {e}")
        
        return state
    
    async def human_review_interrupt(self, state: ResumeProcessingState) -> ResumeProcessingState:
        """Step 7: Interrupt workflow for human review."""
        
        state["current_step"] = "human_review"
        
        # This is where the workflow will pause and wait for human input
        logger.info(f"Workflow paused for human review")
        
        return state
    
    async def apply_approved_changes(self, state: ResumeProcessingState) -> ResumeProcessingState:
        """Step 8: Apply human-approved changes to Notion database."""
        
        state["current_step"] = "apply_changes"
        
        try:
            # Apply changes logic here
            
            state["completed_steps"].append("apply_changes")
            logger.info(f"Applied changes")
            
        except Exception as e:
            state["error_log"].append(f"Apply changes exception: {str(e)}")
            logger.error(f"Apply changes failed: {e}")
        
        return state
    
    async def finalize_processing(self, state: ResumeProcessingState) -> ResumeProcessingState:
        """Step 9: Finalize processing and cleanup."""
        
        state["current_step"] = "finalize"
        
        try:
            # Finalization logic here
            
            state["completed_steps"].append("finalize")
            logger.info(f"Workflow finalized")
            
        except Exception as e:
            state["error_log"].append(f"Finalization exception: {str(e)}")
            logger.error(f"Finalization failed: {e}")
        
        return state

# Factory function to create workflow instance
def create_resume_workflow() -> ResumeProcessingWorkflow:
    """Create and return a configured resume processing workflow."""
    return ResumeProcessingWorkflow() 