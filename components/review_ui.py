import streamlit as st
import asyncio
from typing import TYPE_CHECKING, List, Dict, Any

if TYPE_CHECKING:
    from workflow.pipeline import ResumeProcessingWorkflow

def render_review_tab(workflow_runner: "ResumeProcessingWorkflow"):
    """
    Renders the UI for the Review & Approve tab.
    Allows users to review proposed changes from a resume processing run
    and approve or reject them.
    """
    st.header("Review & Approve Changes")

    if 'latest_workflow_run' not in st.session_state or not st.session_state.latest_workflow_run:
        st.info("No review data available. Please process a resume from the 'Upload & Process' tab first.")
        return

    current_run_state = st.session_state.latest_workflow_run
    proposed_changes: List[Dict[str, Any]] = current_run_state.get('proposed_changes', [])
    review_status = current_run_state.get('review_status')

    if review_status != "PENDING_REVIEW":
        st.info(f"Current document status is '{review_status}'. Review is applicable when status is 'PENDING_REVIEW'.")
        if proposed_changes:
            st.write("However, previously proposed changes are shown below for reference:")
        else:
            st.write("No proposed changes found from the last run.")
            # Optionally, allow re-triggering review if it makes sense for a past state.
            # For now, strict PENDING_REVIEW check for actions.
            return

    if not proposed_changes:
        st.info("No proposed changes to review from the last processing run.")
        return

    st.subheader(f"Proposed Changes for Document ID: {current_run_state.get('document_id')}")

    # Store user selections if we were doing item-by-item approval
    # For MVP, global buttons are used.

    for index, item in enumerate(proposed_changes):
        item_type = item.get('type')

        if item_type == 'NEW_ROLE':
            role_data = item.get('data', {})
            company = role_data.get('company', 'N/A')
            title = role_data.get('title', 'N/A')
            start_year = role_data.get('start_year', 'N/A')
            end_year = role_data.get('end_year', 'N/A')

            with st.expander(f"🆕 NEW ROLE: {title} at {company} ({start_year}-{end_year})", expanded=True):
                st.json(role_data, expanded=False)
                # TODO: Add checkbox for individual approval here if needed in future
                # st.checkbox("Approve this new role", key=f"approve_new_{index}")

        elif item_type == 'MATCHED_ROLE':
            extracted = item.get('extracted_data', {})
            existing = item.get('existing_data', {})
            diff_info = item.get('diff', "No detailed diff available.")

            extr_company = extracted.get('company', 'N/A')
            extr_title = extracted.get('title', 'N/A')
            exist_company = existing.get('company', 'N/A')
            exist_title = existing.get('title', 'N/A')

            with st.expander(f"🔗 MATCHED ROLE: Extracted '{extr_title}' at '{extr_company}' with Existing '{exist_title}' at '{exist_company}'", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Extracted Data")
                    st.json(extracted, expanded=False)
                with col2:
                    st.subheader("Existing Data (Notion)")
                    st.json(existing, expanded=False)
                st.caption(f"Diff Details: {diff_info}")
                # TODO: Add radio buttons for "Keep Existing", "Update with Extracted", "Merge Manually"
                # st.radio("Action for this match", ["Keep Existing", "Update with Extracted"], key=f"action_match_{index}")
        else:
            st.warning(f"Unknown proposed change type: {item_type}")
            st.json(item)

    st.divider()

    # Global action buttons - only active if status is PENDING_REVIEW
    if review_status == "PENDING_REVIEW":
        st.subheader("Review Actions")
        col_approve_new, col_approve_all, col_reject_all = st.columns(3)

        if col_approve_new.button("Approve All NEW Roles", type="primary", key="approve_new_roles_button"):
            trigger_review_workflow(workflow_runner, current_run_state, "REVIEW_APPROVED_NEW")

        # if col_approve_all.button("Approve ALL Changes", key="approve_all_button"): # Needs more complex handling
        #     st.info("Approving all changes (including updates to matched roles) is not fully implemented in MVP.")
            # trigger_review_workflow(workflow_runner, current_run_state, "REVIEW_APPROVED_ALL") # Needs careful implementation

        if col_reject_all.button("Reject All Changes", type="secondary", key="reject_all_button"):
            trigger_review_workflow(workflow_runner, current_run_state, "REVIEW_REJECTED_ALL")
    else:
        st.markdown(f"**Review actions are disabled as current status is '{review_status}'.**")


def trigger_review_workflow(workflow_runner: "ResumeProcessingWorkflow", previous_state: Dict[str, Any], review_outcome: str):
    """
    Triggers a new workflow run with the specified review outcome.
    The workflow should pick up from where it left off or re-process with review decisions.
    For this MVP, it re-runs with the review decision influencing the human_review_node.
    """
    st.info(f"Submitting review decision: {review_outcome}...")

    # Retrieve necessary data from the *original* input that started this whole process
    # This initial_input_data should have been stored in the state by the start_workflow node
    # or passed along. upload_ui.py saves its input_data into the final_state.

    # The `previous_state` is the state from the run that resulted in PENDING_REVIEW.
    # It should contain the `initial_input_data` that `upload_ui` put there.
    initial_input_data_for_this_doc = previous_state.get("initial_input_data", {})

    if not initial_input_data_for_this_doc.get('original_file_path'):
        st.error("Critical error: Could not retrieve original file path from previous state to re-run workflow.")
        return

    # Prepare input_data for the new workflow run, including the review outcome
    rerun_input_data = {
        **initial_input_data_for_this_doc, # Carry over original path, client_id, original doc_id
        'simulated_review_outcome': review_outcome, # This will be read by human_review_node
        'is_review_run': True, # Flag that this is a run triggered from review tab
        # Ensure we pass the proposed_changes from the *previous* state so human_review_node can act on them
        'previous_proposed_changes': previous_state.get('proposed_changes', []),
        'previous_extracted_roles': previous_state.get('extracted_roles', []), # Might be needed if review outcome needs them
        'previous_matched_pairs': previous_state.get('matched_pairs', []),
        'workflow_id': previous_state.get('workflow_id'), # Continue with the same workflow ID
        'document_id': previous_state.get('document_id'), # Continue with the same document ID
    }
    # The `initial_input_data` key within rerun_input_data should also reflect the new review outcome
    rerun_input_data['initial_input_data']['simulated_review_outcome'] = review_outcome


    with st.spinner("Processing review decision... This may take a moment."):
        try:
            # Run the workflow again. The human_review_node will use simulated_review_outcome.
            final_state = asyncio.run(workflow_runner.run(rerun_input_data))
            st.session_state.latest_workflow_run = final_state # Update session state with the new final state

            if final_state:
                st.success(f"Review processed. Final status: {final_state.get('review_status')}")
                if final_state.get('error_log'):
                    st.error("Errors encountered during review processing:")
                    for err in final_state['error_log']:
                        st.caption(f"- {err}")
            else:
                st.error("Workflow did not return a state after review processing.")

            st.rerun() # Rerun the page to reflect updated state and clear review items if status changed

        except Exception as e:
            st.error(f"An error occurred while re-running the workflow for review: {e}")
            import traceback
            st.exception(traceback.format_exc())

# Example of how to display last run details (can be moved to a common utility or app.py sidebar)
# if 'latest_workflow_run' in st.session_state and st.session_state.latest_workflow_run:
#     st.sidebar.subheader("Last Workflow Run (Review Tab)")
#     # ... display logic ...
