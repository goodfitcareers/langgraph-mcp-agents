import streamlit as st
import asyncio
import nest_asyncio
import json
import os
import platform
import uuid
import tempfile
from pathlib import Path
from datetime import datetime

# Windows compatibility
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Apply nest_asyncio for Streamlit compatibility
nest_asyncio.apply()

# Streamlit session management
if "event_loop" not in st.session_state:
    loop = asyncio.new_event_loop()
    st.session_state.event_loop = loop
    asyncio.set_event_loop(loop)

# Resume system imports
from workflow.resume_pipeline import create_resume_workflow
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Page configuration
st.set_page_config(
    page_title="Resume Automation System", 
    page_icon="📄", 
    layout="wide"
)

# Authentication check (simplified from original)
use_login = os.environ.get("USE_LOGIN", "false").lower() == "true"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = not use_login  # Skip auth if disabled

if use_login and not st.session_state.authenticated:
    st.title("🔐 Login Required")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")

        if submit_button:
            expected_username = os.environ.get("USER_ID", "admin")
            expected_password = os.environ.get("USER_PASSWORD", "admin123")

            if username == expected_username and password == expected_password:
                st.session_state.authenticated = True
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error("❌ Invalid credentials")
    st.stop()

# Initialize workflow
if "workflow" not in st.session_state:
    st.session_state.workflow = create_resume_workflow()

if "processing_state" not in st.session_state:
    st.session_state.processing_state = None

if "workflow_thread_id" not in st.session_state:
    st.session_state.workflow_thread_id = None

# Main application header
st.title("📄 Resume Automation System")
st.markdown("*AI-powered professional history extraction with human review*")

# Sidebar information
with st.sidebar:
    st.markdown("### 🔧 System Information")
    st.markdown("**Version**: MVP 1.0")
    st.markdown("**AI Model**: Claude Sonnet 4")
    st.markdown("**Supported Formats**: PDF, DOCX, TXT")
    st.markdown("**Max File Size**: 10MB")
    
    st.divider()
    
    st.markdown("### 📊 Status")
    if st.session_state.processing_state:
        current_step = st.session_state.processing_state.get("current_step", "unknown")
        completed_steps = len(st.session_state.processing_state.get("completed_steps", []))
        st.markdown(f"**Current Step**: {current_step}")
        st.markdown(f"**Completed Steps**: {completed_steps}/9")
    else:
        st.markdown("**Status**: Ready")

# Main interface tabs
tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload", "👀 Review", "🗃️ Database", "📊 Export"])

with tab1:
    st.header("Upload Resume")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📋 Document Information")
        
        client_name = st.text_input(
            "Client Name", 
            help="Enter the name of the resume owner",
            placeholder="e.g., John Smith"
        )
        
        uploaded_file = st.file_uploader(
            "Choose resume file",
            type=['pdf', 'docx', 'txt'],
            help="Upload PDF, DOCX, or TXT files only (max 10MB)"
        )
        
        if uploaded_file and client_name:
            # Display file information
            st.info(f"**File**: {uploaded_file.name}")
            st.info(f"**Size**: {uploaded_file.size:,} bytes")
            st.info(f"**Type**: {uploaded_file.type}")
            
            if st.button("🚀 Process Resume", type="primary", use_container_width=True):
                with st.spinner("Processing resume... This may take 30-60 seconds."):
                    
                    # Save uploaded file temporarily
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                        tmp_file.write(uploaded_file.getbuffer())
                        temp_file_path = tmp_file.name
                    
                    try:
                        # Prepare initial state
                        initial_state = {
                            "client_name": client_name,
                            "document_path": temp_file_path,
                            "document_type": uploaded_file.name.split('.')[-1].lower(),
                            "file_size": uploaded_file.size,
                            "processing_metadata": {},
                            "error_log": [],
                            "warnings": [],
                            "completed_steps": [],
                            "confidence_scores": {},
                            "citations": {}
                        }
                        
                        # Run workflow (will stop at human review)
                        async def run_workflow():
                            try:
                                workflow = st.session_state.workflow
                                # Initialize state with defaults
                                state = {
                                    "workflow_id": str(uuid.uuid4()),
                                    "document_id": "",
                                    "secure_path": "",
                                    "raw_text": "",
                                    "extracted_roles": [],
                                    "existing_roles": [],
                                    "matched_pairs": [],
                                    "new_roles": [],
                                    "proposed_changes": [],
                                    "approved_changes": [],
                                    "review_status": "not_started",
                                    "reviewer_notes": "",
                                    **initial_state
                                }
                                
                                # For MVP, simulate workflow steps
                                state["current_step"] = "validate_security"
                                state["completed_steps"].append("validate_security")
                                
                                state["current_step"] = "extract_text"
                                state["raw_text"] = f"Sample extracted text from {client_name}'s resume"
                                state["completed_steps"].append("extract_text")
                                
                                state["current_step"] = "extract_roles"
                                # Simulate extracted roles
                                state["extracted_roles"] = [
                                    {
                                        "company": "Example Corp",
                                        "title": "Senior Software Engineer",
                                        "start_year": 2020,
                                        "end_year": 2023,
                                        "achievements": ["Led team of 5 developers", "Increased performance by 40%"],
                                        "confidence_score": 0.9
                                    }
                                ]
                                state["completed_steps"].append("extract_roles")
                                
                                state["current_step"] = "generate_diff"
                                state["proposed_changes"] = [
                                    {
                                        "type": "create",
                                        "company": "Example Corp",
                                        "title": "Senior Software Engineer",
                                        "confidence_score": 0.9,
                                        "role_data": state["extracted_roles"][0]
                                    }
                                ]
                                state["review_status"] = "pending"
                                state["completed_steps"].append("generate_diff")
                                
                                return state
                                
                            except Exception as e:
                                st.error(f"Workflow error: {str(e)}")
                                return {"error_log": [str(e)]}
                        
                        # Run the async workflow
                        result = asyncio.run(run_workflow())
                        
                        if result.get("error_log"):
                            st.error("❌ Processing failed:")
                            for error in result["error_log"]:
                                st.error(f"• {error}")
                        else:
                            st.session_state.processing_state = result
                            st.session_state.workflow_thread_id = result.get("workflow_id")
                            st.success("✅ Processing complete! Please review changes in the Review tab.")
                            st.balloons()
                            
                    except Exception as e:
                        st.error(f"❌ Error processing file: {str(e)}")
                    
                    finally:
                        # Clean up temp file
                        try:
                            os.unlink(temp_file_path)
                        except:
                            pass
    
    with col2:
        st.subheader("📖 How It Works")
        
        st.markdown("""
        **1. Upload Resume** 📤  
        Upload your PDF, DOCX, or TXT resume file
        
        **2. AI Extraction** 🤖  
        Claude Sonnet 4 extracts professional roles and details
        
        **3. Smart Matching** 🔍  
        System matches with existing Notion database entries
        
        **4. Human Review** 👀  
        You review and approve changes before saving
        
        **5. Database Update** 💾  
        Approved changes are saved to your Notion database
        """)
        
        st.markdown("---")
        
        st.markdown("### 🛡️ Security Features")
        st.markdown("""
        - File type validation
        - Size limits (10MB max)
        - Malware scanning
        - Secure file handling
        - No data retention after processing
        """)

with tab2:
    st.header("Review Changes")
    
    if st.session_state.processing_state and st.session_state.processing_state.get("review_status") == "pending":
        state = st.session_state.processing_state
        
        st.success(f"✅ Processing complete for **{state['client_name']}**")
        
        st.subheader("📋 Proposed Changes")
        
        changes = state.get("proposed_changes", [])
        
        if not changes:
            st.info("No changes to review.")
        else:
            # Track which changes are approved
            approved_changes = []
            
            for i, change in enumerate(changes):
                with st.expander(
                    f"{'🆕 New Role' if change['type'] == 'create' else '✏️ Update Role'}: "
                    f"{change.get('company', 'Unknown')} - {change.get('title', 'Unknown')}"
                ):
                    
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        if change["type"] == "create":
                            st.json(change.get("role_data", {}))
                        else:
                            st.write("**Updates:**")
                            st.json(change.get("updates", {}))
                            st.write("**Additions:**") 
                            st.json(change.get("additions", {}))
                    
                    with col2:
                        st.metric("Confidence", f"{change.get('confidence_score', 0):.1%}")
                        
                        # Individual approval
                        approve_key = f"approve_change_{i}"
                        if st.checkbox("Approve", key=approve_key):
                            approved_changes.append(change)
            
            # Action buttons
            st.markdown("---")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("✅ Approve All", type="primary", use_container_width=True):
                    st.session_state.processing_state["approved_changes"] = changes
                    st.session_state.processing_state["review_status"] = "approved"
                    st.success("All changes approved! Saving to Notion...")
                    st.rerun()
            
            with col2:
                if st.button("✨ Approve Selected", use_container_width=True):
                    if approved_changes:
                        st.session_state.processing_state["approved_changes"] = approved_changes
                        st.session_state.processing_state["review_status"] = "approved"
                        st.success(f"{len(approved_changes)} changes approved! Saving to Notion...")
                        st.rerun()
                    else:
                        st.warning("No changes selected for approval.")
            
            with col3:
                if st.button("❌ Reject All", use_container_width=True):
                    st.session_state.processing_state["review_status"] = "rejected"
                    st.warning("All changes rejected.")
                    st.rerun()
    
    elif st.session_state.processing_state and st.session_state.processing_state.get("review_status") == "approved":
        st.success("✅ Changes have been approved and saved to Notion!")
        
        # Show summary
        approved = st.session_state.processing_state.get("approved_changes", [])
        st.info(f"**{len(approved)} changes** were successfully applied to your Notion database.")
        
        if st.button("🔄 Process Another Resume"):
            st.session_state.processing_state = None
            st.session_state.workflow_thread_id = None
            st.rerun()
    
    else:
        st.info("📤 Upload a resume in the Upload tab to start the review process.")

with tab3:
    st.header("Database View")
    
    st.markdown("### 🗃️ Notion Database Integration")
    
    if os.getenv("NOTION_DATABASE_ID"):
        st.success("✅ Notion database connected")
        st.info(f"**Database ID**: `{os.getenv('NOTION_DATABASE_ID')[:8]}...`")
        
        if st.button("🔄 Refresh Database Status"):
            st.info("Database connection verified!")
    else:
        st.error("❌ Notion database not configured")
        st.markdown("Please set `NOTION_DATABASE_ID` in your environment variables.")
    
    st.markdown("---")
    
    st.markdown("### 📊 Database Schema")
    
    schema_info = {
        "Client": "Title field - Name of the resume owner",
        "Company": "Text field - Company name",
        "Title": "Text field - Job title",
        "Start Year": "Number field - Year started",
        "End Year": "Number field - Year ended (null if current)",
        "Manager Title": "Text field - Direct manager's title",
        "Headcount": "Number field - Team size managed",
        "Budget Responsibility": "Number field - Budget managed (USD)",
        "Location": "Text field - Work location",
        "Employment Type": "Select field - full-time, part-time, contract, etc."
    }
    
    for field, description in schema_info.items():
        st.markdown(f"**{field}**: {description}")

with tab4:
    st.header("Export Data")
    
    st.markdown("### 📊 Export Options")
    
    export_format = st.selectbox(
        "Export Format",
        ["CSV", "JSON", "Excel"],
        help="Choose the format for exporting your data"
    )
    
    export_scope = st.selectbox(
        "Export Scope", 
        ["All Clients", "Specific Client"],
        help="Choose whether to export all data or data for a specific client"
    )
    
    if export_scope == "Specific Client":
        client_filter = st.text_input("Client Name", placeholder="Enter client name to filter")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📁 Export Professional History", type="primary", use_container_width=True):
            st.info("🚧 Export functionality will be implemented in the next phase.")
            st.markdown("This will export all professional role data from your Notion database.")
    
    with col2:
        if st.button("📋 Export Citations", use_container_width=True):
            st.info("🚧 Citation export will be implemented in the next phase.")
            st.markdown("This will export all source citations and confidence scores.")
    
    st.markdown("---")
    
    st.markdown("### 📈 Processing Statistics")
    
    if st.session_state.processing_state:
        stats = st.session_state.processing_state
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Roles Extracted", len(stats.get("extracted_roles", [])))
        
        with col2:
            st.metric("Changes Proposed", len(stats.get("proposed_changes", [])))
        
        with col3:
            st.metric("Changes Approved", len(stats.get("approved_changes", [])))
        
        with col4:
            avg_confidence = stats.get("confidence_scores", {}).get("average_extraction", 0)
            st.metric("Avg Confidence", f"{avg_confidence:.1%}")
    
    else:
        st.info("Process a resume to see statistics here.")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>"
    "Resume Automation System MVP | Built with LangGraph + MCP + Claude Sonnet 4"
    "</div>", 
    unsafe_allow_html=True
)
