import streamlit as st
import os
import uuid
import asyncio
from datetime import datetime

# Assuming ResumeProcessingWorkflow is in workflow.pipeline
# Adjust import path if necessary based on your project structure
from workflow.pipeline import ResumeProcessingWorkflow


def render_upload_tab(workflow_runner: ResumeProcessingWorkflow):
    """
    Renders the UI for the resume upload tab.
    Allows users to upload resume files and initiate the processing workflow.
    """
    st.header("Upload Resume for Processing")

    # Get allowed extensions and max file size from environment variables
    allowed_extensions_str = os.environ.get("ALLOWED_EXTENSIONS", ".pdf,.docx,.doc,.txt")
    allowed_extensions = [ext.strip() for ext in allowed_extensions_str.split(',')]

    try:
        # Note: Streamlit's st.file_uploader uses bytes for size, not MB directly in its own check.
        # This MAX_FILE_SIZE_MB is for our own validation if needed, or for informing the user.
        # Streamlit has a server config `server.maxUploadSize` which is the ultimate limit.
        max_size_mb = int(os.environ.get("MAX_FILE_SIZE_MB", 10))
    except ValueError:
        max_size_mb = 10
        st.warning(f"Invalid MAX_FILE_SIZE_MB environment variable. Defaulting to {max_size_mb}MB.")

    uploaded_file = st.file_uploader(
        f"Choose a resume file ({', '.join(allowed_extensions)}, max {max_size_mb}MB)",
        type=[ext.lstrip('.') for ext in allowed_extensions], # Streamlit expects list of extensions without dot
        accept_multiple_files=False,
        help=f"Supported formats: {allowed_extensions_str}. Maximum file size: {max_size_mb}MB."
    )

    client_id = st.text_input(
        "Client ID (Optional)",
        value="default_client",
        help="Enter a client identifier if applicable."
    )

    # Add a way to select simulated review outcome for testing
    # In a real app, this would not be here.
    simulated_review_options = ["APPROVE_ALL_NEW", "APPROVE_ALL", "REJECT_ALL"]
    simulated_review_outcome = st.selectbox(
        "Simulated Review Outcome (for testing)",
        options=simulated_review_options,
        index=0,
        help="Determines the simulated human review action in the workflow."
    )

    if st.button("Process Resume", type="primary"):
        if uploaded_file is not None:
            # Validate file size before saving (Streamlit might also enforce this)
            if uploaded_file.size > max_size_mb * 1024 * 1024:
                st.error(f"File size exceeds the {max_size_mb}MB limit. Please upload a smaller file.")
                return

            # Ensure the 'static/uploads' directory exists
            upload_dir = os.path.join("static", "uploads")
            os.makedirs(upload_dir, exist_ok=True)

            # Create a unique filename to avoid overwrites
            file_extension = os.path.splitext(uploaded_file.name)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            saved_file_path = os.path.join(upload_dir, unique_filename)

            try:
                with open(saved_file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success(f"File '{uploaded_file.name}' uploaded successfully as '{unique_filename}'.")

                # Prepare input data for the workflow
                # document_id can be generated here or within the workflow's start node
                doc_id = str(uuid.uuid4())
                input_data = {
                    'original_file_path': saved_file_path,
                    'client_id': client_id,
                    'document_id': doc_id, # Pass a pre-generated doc_id
                    'simulated_review_outcome': simulated_review_outcome, # For testing the review process
                    # Pass the initial_input_data itself so nodes can access it if needed, like human_review_node
                    'initial_input_data': {
                        'simulated_review_outcome': simulated_review_outcome
                    }
                }

                # Initialize a placeholder for live updates if possible (more advanced)
                # status_placeholder = st.empty()
                # status_placeholder.info("Starting workflow...")

                with st.spinner("Processing resume... This may take a moment."):
                    # Run the workflow
                    # Streamlit runs in an asyncio event loop, so direct asyncio.run might cause issues.
                    # If workflow_runner.run is an async function:
                    try:
                        # Using st.session_state.event_loop if available from app.py
                        if "event_loop" in st.session_state and st.session_state.event_loop.is_running():
                             # Schedule the coroutine on the existing loop if possible
                             # This is complex; for MVP, direct call might work if nest_asyncio is robust.
                             # Or, run in a separate thread if true parallelism is needed.
                             # For now, let's try direct await if nest_asyncio is effective.
                             # However, Streamlit buttons are not async, so we need asyncio.run or similar.

                             # This is a common pattern for Streamlit:
                             final_state = asyncio.run(workflow_runner.run(input_data))
                        else:
                             # Fallback if no loop is in session_state, or it's not running
                             final_state = asyncio.run(workflow_runner.run(input_data))

                        st.session_state.latest_workflow_run = final_state
                        st.session_state.last_processed_doc_id = doc_id # Store for other tabs

                        # status_placeholder.empty() # Clear the "Starting workflow..." message

                        # Display results
                        if final_state:
                            st.subheader("Processing Complete")
                            st.write(f"Workflow ID: {final_state.get('workflow_id')}")
                            st.write(f"Document ID: {final_state.get('document_id')}")
                            st.write(f"Final Review Status: {final_state.get('review_status')}")
                            st.write(f"Final Task Info: {final_state.get('current_task_info')}")

                            if final_state.get('error_log'):
                                st.error("Errors encountered during processing:")
                                for err in final_state['error_log']:
                                    st.caption(f"- {err}")
                            else:
                                st.success("Workflow completed without critical errors logged in the state.")

                            # Provide some extracted data summary if available
                            if final_state.get('extracted_roles'):
                                st.info(f"Extracted {len(final_state['extracted_roles'])} roles.")
                            if final_state.get('new_roles'):
                                st.info(f"Identified {len(final_state['new_roles'])} new roles.")
                            if final_state.get('matched_pairs'):
                                st.info(f"Matched {len(final_state['matched_pairs'])} existing roles.")

                        else:
                            st.error("Workflow did not return a final state.")

                    except Exception as e:
                        # status_placeholder.empty()
                        st.error(f"An error occurred while running the workflow: {e}")
                        import traceback
                        st.exception(traceback.format_exc())

            except Exception as e:
                st.error(f"An error occurred during file saving or workflow preparation: {e}")
        else:
            st.warning("Please upload a resume file first.")

    # Display information about the last run if it exists in session state
    if 'latest_workflow_run' in st.session_state and st.session_state.latest_workflow_run:
        st.sidebar.subheader("Last Workflow Run Details")
        last_run_state = st.session_state.latest_workflow_run
        st.sidebar.caption(f"ID: {last_run_state.get('workflow_id')}")
        st.sidebar.caption(f"Doc ID: {last_run_state.get('document_id')}")
        st.sidebar.caption(f"Status: {last_run_state.get('review_status')}")
        if st.sidebar.button("Show Full Last State", key="show_last_state_upload_tab"):
            st.sidebar.json(last_run_state, expanded=False)
