import streamlit as st
import asyncio
import nest_asyncio
import json
import os
import platform

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Apply nest_asyncio: Allow nested calls within an already running event loop
nest_asyncio.apply()

# Create and reuse global event loop (create once and continue using)
# This is important for Streamlit's execution model with asyncio
if "event_loop" not in st.session_state:
    st.session_state.event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(st.session_state.event_loop)


from dotenv import load_dotenv
from workflow.pipeline import ResumeProcessingWorkflow
from components.upload_ui import render_upload_tab
from components.review_ui import render_review_tab
# from components.database_ui import render_database_tab # For future
# from components.export_ui import render_export_tab # For future


# Load environment variables (get API keys and settings from .env file)
load_dotenv(override=True)


# --- Page Configuration (must be the first Streamlit command) ---
st.set_page_config(
    page_title="Resume Automation System",
    page_icon="📄",
    layout="wide" # Use wide layout for better use of space
)


# --- Authentication ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

use_login = os.environ.get("USE_LOGIN", "false").lower() == "true"

if use_login and not st.session_state.authenticated:
    # If login is used, set page config for login page specifically if different
    # st.set_page_config(page_title="Login - Resume Automation", layout="centered") # Example
    st.title("🔐 Login Required")
    st.markdown("Please log in to access the Resume Automation System.")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")

        if submit_button:
            expected_username = os.environ.get("APP_USERNAME", "admin") # Use APP_USERNAME from .env
            # Password should be compared with a HASH stored in .env (APP_PASSWORD_HASH)
            # For MVP, direct comparison might be used, but this is NOT secure for production.
            # Example: if username == expected_username and bcrypt.checkpw(password.encode(), APP_PASSWORD_HASH.encode()):
            expected_password = os.environ.get("APP_PASSWORD_HASH", "password") # Placeholder if hash not set

            if username == expected_username and password == expected_password: # Insecure direct password check
                st.session_state.authenticated = True
                st.success("✅ Login successful! Refreshing...")
                st.rerun() # Rerun to load the main app UI
            else:
                st.error("❌ Invalid username or password.")
    st.stop() # Do not render the rest of the app if not authenticated


# --- Workflow Initialization ---
# Instantiate the workflow runner once and store in session state if needed,
# or just pass the instance around. For simplicity, creating it once.
if 'workflow_manager' not in st.session_state:
    try:
        st.session_state.workflow_manager = ResumeProcessingWorkflow()
        print("ResumeProcessingWorkflow initialized and stored in session state.")
    except Exception as e:
        st.error(f"Failed to initialize Resume Processing Workflow: {e}")
        st.stop() # Stop if workflow cannot be initialized

workflow_manager = st.session_state.workflow_manager


# --- Sidebar ---
st.sidebar.markdown("### ✍️ Resume Automation System")
st.sidebar.markdown("Streamline your resume processing.")
st.sidebar.divider()

# Model selection (kept for now, acknowledge it's not directly wired to current workflow's LLM)
# The workflow uses PRIMARY_MODEL from .env. This could be for future features.
st.sidebar.subheader("⚙️ System Settings (Future Use)")
available_models_env = os.environ.get("AVAILABLE_MODELS", PRIMARY_MODEL) # Example: "model1,model2"
available_models = [m.strip() for m in available_models_env.split(',')]

if "selected_model" not in st.session_state:
     st.session_state.selected_model = os.environ.get("PRIMARY_MODEL", "claude-3-5-sonnet-20240620")

selected_model_sidebar = st.sidebar.selectbox(
    "🤖 Select Model (for potential future use)",
    options=available_models,
    index=(
        available_models.index(st.session_state.selected_model)
        if st.session_state.selected_model in available_models
        else 0
    ),
    help="This model selection is for potential future features. Current workflow uses PRIMARY_MODEL from .env.",
)
if selected_model_sidebar != st.session_state.selected_model:
    st.session_state.selected_model = selected_model_sidebar
    # No re-initialization tied to this for now as workflow is static regarding this model choice.
    st.sidebar.info(f"Model selection changed to {selected_model_sidebar}. (Note: Workflow uses PRIMARY_MODEL from .env)")

# Timeout and Recursion limits (can be removed if not used by any component)
# For now, keeping them as they might be relevant for direct LLM calls outside workflow, or future agentic parts.
if "timeout_seconds" not in st.session_state:
    st.session_state.timeout_seconds = 120
if "recursion_limit" not in st.session_state:
    st.session_state.recursion_limit = 100
    
st.session_state.timeout_seconds = st.sidebar.slider(
    "⏱️ Timeout (seconds, future use)", min_value=60, max_value=300,
    value=st.session_state.timeout_seconds, step=10
)
st.session_state.recursion_limit = st.sidebar.slider(
    "🔄 Recursion Limit (future use)", min_value=10, max_value=200,
    value=st.session_state.recursion_limit, step=10
)

st.sidebar.divider()
if use_login:
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.success("✅ Logged out successfully.")
        st.rerun()


# --- Main Application UI with Tabs ---
st.title("📄 Resume Automation System")

tab_upload, tab_review, tab_database, tab_export = st.tabs([
    "📤 Upload & Process",
    "📝 Review & Approve",
    "🗃️ View Database",
    "📊 Export Data"
])

with tab_upload:
    if workflow_manager:
        render_upload_tab(workflow_manager)
    else:
        st.error("Workflow manager is not available. Upload functionality disabled.")

with tab_review:
    if workflow_manager:
        render_review_tab(workflow_manager)
    else:
        st.error("Workflow manager is not available. Review functionality disabled.")
    # Example: if 'latest_workflow_run' in st.session_state:
    #    render_review_tab(st.session_state.latest_workflow_run, workflow_manager) # Pass workflow_manager

with tab_database:
    st.header("View Notion Database")
    st.write("This section will provide a way to view and interact with the professional history data stored in the Notion database.")
    st.info("🚧 Feature under construction.")
    # Example: render_database_tab()

with tab_export:
    st.header("Export Data")
    st.write("This section will allow users to export processed data in various formats (e.g., CSV, JSON).")
    st.info("🚧 Feature under construction.")
    # Example: render_export_tab()


# --- Cleanup of old UI elements ---
# Removed: SYSTEM_PROMPT, OUTPUT_TOKEN_INFO, old session state init related to agent/history/mcp_client,
# print_message(), get_streaming_callback(), process_query(), initialize_session() (old MCP one),
# old sidebar for tool management, direct chat input logic.
# The new UI is tab-based and driven by the workflow.
