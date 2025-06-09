# Documentation Plan for Resume Automation System

This document outlines the plan for creating and updating documentation for the Resume Automation System.

## 1. `README.md` Updates

The main `README.md` is the primary entry point for users and developers. It needs significant updates to reflect the new system architecture and functionality.

*   **Rewrite Introduction:**
    *   Clearly state the purpose of the Resume Automation System.
    *   Highlight its key benefits (e.g., automated extraction, Notion integration, citation tracking, review workflow).
*   **Update "Project Overview":**
    *   Describe the new architecture focusing on the Streamlit UI, LangGraph workflow, and MCP (Multi-Component Process) servers.
    *   Mention the shift from a generic ReAct agent to a structured workflow.
*   **Update "Features":**
    *   List current features:
        *   Resume uploading (PDF, DOCX, TXT).
        *   Automated text extraction.
        *   LLM-based extraction of professional history (companies, roles, dates, achievements, responsibilities).
        *   Matching extracted roles against existing entries in a Notion database.
        *   (Simulated) Human review and approval interface for new/matched roles.
        *   Automated saving of approved new roles to Notion.
        *   Citation tracking for extracted information, linking back to source documents and Notion entries.
        *   Ability to view the Notion database contents within the app.
        *   Data export functionality (Notion roles as CSV, citations as JSON).
        *   Basic authentication for the UI.
        *   Configurable via environment variables.
        *   Docker support for deployment.
*   **Architecture Diagram:**
    *   Create a new architecture diagram illustrating:
        *   Streamlit UI (with tabs: Upload, Review, Database, Export).
        *   LangGraph `ResumeProcessingWorkflow`.
        *   Interactions with MCP Servers:
            *   `SecurityGatewayMCP`
            *   `DocumentProcessorMCP` (and its interaction with `FileParser`)
            *   `NotionIntegrationMCP`
            *   `CitationTrackerMCP` (and its PostgreSQL database).
        *   Notion Database as the external data store.
    *   The diagram should show the flow of data and control.
*   **Revised "Quick Start" / "Getting Started":**
    *   Prerequisites (Python, Docker, PostgreSQL, Notion account).
    *   Cloning the repository.
    *   Setting up the environment:
        *   Python virtual environment.
        *   `pip install -r requirements.txt`.
        *   Copying `.env.example` to `.env` and filling in **all** required variables (emphasize `NOTION_TOKEN`, `NOTION_DATABASE_ID`, `DATABASE_URL`, `ANTHROPIC_API_KEY`, `APP_USERNAME`, `APP_PASSWORD_HASH`).
    *   Database setup: `psql -f setup_db.sql` (if a script is provided) or manual steps for `init_citation_db`.
    *   Notion database setup (linking to detailed instructions in `DEPLOYMENT.md` or a new section).
    *   Running the application (e.g., `streamlit run app.py` or `docker-compose up`).
*   **Revised "Usage" Section:**
    *   Brief walkthrough of using the Streamlit UI (refer to User Guide for details).
*   **MCP Server Configuration:**
    *   Briefly explain `resume_mcp_config.json` and its role.
*   **Development Section:**
    *   Setting up for development.
    *   Running tests.
    *   Information on MCP server architecture if developers need to add new ones.
*   **Remove/Update Outdated Sections:**
    *   Remove or significantly update sections related to the old generic MCP tool management or ReAct agent if they are too prominent or misleading.

## 2. MCP Server API Documentation

While not a public API, documenting the MCP server tools is useful for developers maintaining or extending the system. This could be a new file (`MCP_API.md`) or a subsection in the `README.md` or a developers guide.

For each MCP server (`SecurityGateway`, `DocumentProcessor`, `NotionIntegration`, `CitationTracker`):
*   **Purpose:** Brief description of the server's role.
*   **Tools:** For each `@mcp.tool()`:
    *   Name of the tool.
    *   Purpose.
    *   Parameters (name, type, description, optional/required).
    *   Return value (structure, type, meaning of fields, example).
    *   Potential errors or specific failure responses.

## 3. User Guide (Streamlit UI)

This guide will help end-users navigate and use the Streamlit application. It could be a `USER_GUIDE.md` file or integrated into the `README.md`.

*   **Introduction:** Brief overview of what the system does for the user.
*   **Logging In:** How to log in if authentication is enabled.
*   **Upload & Process Tab:**
    *   How to upload a resume file (supported formats, size limits).
    *   Entering `Client ID` (if its purpose is user-facing).
    *   Understanding the "Simulated Review Outcome" dropdown (explain it's for testing/demo).
    *   What happens after clicking "Process Resume".
    *   Interpreting processing messages and results displayed on this tab.
*   **Review & Approve Tab:**
    *   When and how to use this tab (after a document is processed and is `PENDING_REVIEW`).
    *   Understanding the display of "New Roles" and "Matched Roles".
    *   How to use the "Approve All New Roles" and "Reject All" buttons.
    *   What happens after submitting a review decision.
*   **View Database Tab:**
    *   How to use the "Refresh Data from Notion" button.
    *   Understanding the displayed table of roles.
    *   Using the expanders to view detailed information for each role.
*   **Export Data Tab:**
    *   How to prepare and download professional history data as CSV.
    *   How to prepare and download citation data as JSON.
    *   How to download the last workflow run state.
*   **Troubleshooting (Basic):**
    *   Common error messages and what they mean (e.g., "Notion token not set").
    *   What to do if a workflow run fails.

## 4. Deployment Guide

The `DEPLOYMENT.md` file (created in the previous step) will serve as the primary deployment guide. Ensure it's comprehensive and covers all necessary aspects as outlined.
*   Cross-reference with `README.md` for initial setup where appropriate.

## 5. Security Information

A brief section or a separate `SECURITY.md` file.
*   **Data Handling:**
    *   Where uploaded files are stored (`static/uploads/`) and if/when they are deleted.
    *   Briefly mention data flow (resume -> text -> LLM -> Notion/DB).
*   **Authentication:**
    *   Details about the Streamlit UI authentication (username/password).
    *   Emphasis on using a strong, bcrypt-hashed password for `APP_PASSWORD_HASH`.
*   **Secrets Management:**
    *   Reiterate the importance of using `.env` for local development and environment variables/secrets management in deployment (as detailed in `DEPLOYMENT.md`).
*   **File Validation:**
    *   Mention checks for file type and size.
    *   Current status of malware scanning (e.g., placeholder, or if ClamAV is active).
*   **External Services:**
    *   Note reliance on Notion and Anthropic (or other LLM provider) APIs and their respective security implications.

## Plan for Execution:
1.  **Priority 1: `README.md` Rework.** This is the most critical document for anyone encountering the project.
2.  **Priority 2: `DEPLOYMENT.md` Finalization.** Ensure it's accurate and complete.
3.  **Priority 3: User Guide.** Create content for Streamlit UI usage.
4.  **Priority 4: MCP API Documentation & Security Information.** Document internal APIs and security aspects for developers and maintainers.

This plan aims to provide comprehensive documentation for both users and developers of the Resume Automation System.
