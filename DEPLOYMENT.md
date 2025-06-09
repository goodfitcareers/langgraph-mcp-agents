# Deployment Considerations for Resume Automation System

This document outlines key considerations for deploying the Resume Automation System.

## I. Environment Setup

### 1. Python Version
- Ensure Python 3.9+ is installed on the deployment server. (Verify exact version compatibility from `pyproject.toml` or project requirements).

### 2. Dependencies
- **`requirements.txt`**: All Python dependencies are listed here. Install using `pip install -r requirements.txt`.
- **System-level Dependencies**:
    - **PostgreSQL Client Libraries**: Required for `psycopg2` to connect to the PostgreSQL database (e.g., `libpq-dev` on Debian/Ubuntu).
    - **ClamAV (Optional)**: If malware scanning via `pyclamd` or direct ClamAV calls is fully implemented in the Security Gateway, the ClamAV daemon (`clamd`) must be installed and running on the server or accessible via network.
    - **`antiword` or `libreoffice` (Optional)**: If robust `.doc` file parsing is required (beyond what `python-docx` can handle), these tools might be needed by `parsers.file_parser`.

## II. Application Configuration

### 1. Environment Variables (`.env` file)
A `.env` file is crucial for configuring the application. Refer to `.env.example` for a complete list. Key variables include:
- **Database:**
    - `DATABASE_URL`: PostgreSQL connection string (e.g., `postgresql://user:pass@host:port/dbname`).
- **Notion Integration:**
    - `NOTION_TOKEN`: Notion API integration token.
    - `NOTION_DATABASE_ID`: ID of the Notion database where professional history will be stored.
- **LLM API Keys:**
    - `ANTHROPIC_API_KEY`: For Claude models.
    - `OPENAI_API_KEY` (If OpenAI models are also supported/used).
- **Application Settings:**
    - `PRIMARY_MODEL`: Default LLM model for extraction (e.g., `claude-3-5-sonnet-20240620`).
    - `ALLOWED_EXTENSIONS`: Comma-separated list of allowed file extensions (e.g., `.pdf,.docx,.txt`).
    - `MAX_FILE_SIZE_MB`: Maximum allowed upload file size.
- **Security & Authentication (Streamlit App):**
    - `USE_LOGIN`: Set to `true` to enable username/password authentication for the Streamlit UI.
    - `APP_USERNAME`: Username for UI login.
    - `APP_PASSWORD_HASH`: **BCRYPT HASH** of the password for UI login. Do not store plain text passwords. Generate using a bcrypt utility.
    - `SECRETS_KEY_FOR_SESSION_MANAGEMENT`: Strong random key for Streamlit session state encryption or other security measures.
- **MCP Server Configuration:**
    - `resume_mcp_config.json`: This file defines how MCP servers are run. Paths within this file (e.g., to Python scripts for servers) must be correct for the deployment environment. If deploying with Docker, these paths should be relative to the Docker container's file system.

### 2. `static/uploads` Directory
- The application saves uploaded resume files to `static/uploads/`. Ensure this directory exists and the application has write permissions to it.
- Consider a strategy for cleaning up old files from this directory if it's not intended for long-term storage.

## III. Database Setup (PostgreSQL)

- **Installation**: A PostgreSQL server (version 12+ recommended) must be running and accessible.
- **Database Creation**: Create a dedicated database for the application.
- **User and Permissions**: Create a user with appropriate permissions (CONNECT, CREATE, SELECT, INSERT, UPDATE, DELETE) on the database and its tables.
- **Table Initialization**:
    - The `citations` table is managed by the `CitationTrackerMCP` server.
    - The `init_citation_db()` function in `mcp_servers/citation_tracker.py` attempts to create the table if it doesn't exist when the server starts.
    - For production, it's recommended to run this initialization script manually or via a deployment script to ensure the table schema is correctly set up before the application runs.
    - Schema: `citation_id UUID PK, source_document_fingerprint TEXT, original_extracted_text TEXT, document_id TEXT, page_number INTEGER, paragraph_number INTEGER, custom_location_info TEXT, notion_page_id TEXT, notion_field_name TEXT, timestamp TIMESTAMPTZ`.

## IV. Notion Setup

1.  **Create a Notion Integration:**
    *   Go to [Notion My Integrations](https://www.notion.so/my-integrations).
    *   Create a new integration.
    *   Capabilities: Ensure it can Read, Insert, and Update content. It also needs to Read user information if that becomes relevant.
    *   Copy the "Internal Integration Token" – this is your `NOTION_TOKEN`.
2.  **Create the Target Notion Database:**
    *   Create a new full-page database in your Notion workspace.
    *   The database ID (found in the URL or when sharing the DB with the integration) is your `NOTION_DATABASE_ID`.
3.  **Define Database Properties:**
    *   The Notion database **must** have properties (columns) that match the fields defined in `NotionProfessionalHistorySchema` (`mcp_servers/notion_integration.py`). The names must match what `map_schema_to_notion_properties` expects.
    *   **Key Properties & Types (Example):**
        *   `Company`: `Title` (Primary property for the page title)
        *   `Title`: `Rich Text`
        *   `Start Year`: `Number`
        *   `End Year`: `Number` (or `Rich Text` if storing "Present")
        *   `Manager Title`: `Rich Text`
        *   `Direct Reports`: `Number` (or `Rich Text` if storing text like "team of 5-8")
        *   `Budget Responsibility`: `Number` (or `Rich Text`)
        *   `Headcount`: `Number`
        *   `Quota`: `Number` (or `Rich Text`)
        *   `Peer Functions`: `Rich Text` (store as JSON string or comma-separated) or `Multi-select`
        *   `Achievements`: `Rich Text` (store as JSON string of list items, or bullet points)
        *   `Responsibilities`: `Rich Text` (store as JSON string or bullet points)
        *   `Sources`: `Rich Text` (store as JSON string)
        *   `Confidence Score`: `Number` (Format: Number with decimals)
        *   `Last Updated`: `Date` (Property type: Date)
    *   Ensure the property types in Notion are compatible with how data is formatted by `map_schema_to_notion_properties`.
4.  **Share the Database with the Integration:**
    *   Open the Notion database.
    *   Click the "..." menu (top right).
    *   Go to "Add connections" (or "Open in..." then "Connections" depending on Notion UI version).
    *   Find and select your created integration to give it access to this database.

## V. Dockerization (Recommended)

### 1. `Dockerfile`
- A `Dockerfile` should be created at the project root to build the application image.
- It should:
    - Start from a Python base image (e.g., `python:3.9-slim`).
    - Set up a working directory (e.g., `/app`).
    - Copy `requirements.txt` and install dependencies.
    - Copy the entire application source code into the image.
    - Expose the Streamlit port (default 8501).
    - Define the command to run the Streamlit application (e.g., `streamlit run app.py`).
    - Ensure any necessary system-level dependencies are installed (see Section I.2).

### 2. `docker-compose.yaml` (from `dockers/docker-compose.yaml`)
- The existing `docker-compose.yaml` likely defines services for the application and potentially PostgreSQL and ClamAV.
- **Application Service (`app`):**
    - Should build from the `Dockerfile`.
    - Mount volumes for persistent data if needed (e.g., `static/uploads` if not ephemeral, though usually uploads are temporary or moved to proper storage).
    - Pass environment variables from a `.env` file (e.g., `env_file: .env`).
    - Map ports (e.g., `8501:8501`).
    - Ensure `resume_mcp_config.json` paths are correct within the container context. If MCP servers are run as separate processes *within the same container* as the Streamlit app, paths might be relative. If MCP servers are separate Docker services, `resume_mcp_config.json` would need to reflect how to reach them (e.g., using Docker service names as hostnames and appropriate ports if they use network transport instead of stdio).
        *Current `resume_mcp_config.json` uses stdio, implying MCP servers are Python scripts run as subprocesses. This is compatible with running them in the same container as the main app.*
- **PostgreSQL Service (`db`):**
    - Use an official PostgreSQL image (e.g., `postgres:15`).
    - Configure environment variables for `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.
    - Set up a volume for persistent database storage (e.g., `pg_data:/var/lib/postgresql/data`).
- **ClamAV Service (`clamav` - Optional):**
    - If used, include a ClamAV service (e.g., from `clamav/clamav:latest`).
    - Configure it to update its virus definitions.
    - The application service would connect to it (likely via TCP if `pyclamd` is configured for network).

### 3. Building and Running with Docker
- Build: `docker-compose build`
- Run: `docker-compose up -d`

## VI. Replit Deployment (Alternative/Optional)

- **Setup:**
    - Import the project from GitHub.
    - Replit usually auto-detects Python and installs dependencies from `requirements.txt` via Poetry or Pip.
- **Environment Variables:**
    - Use Replit "Secrets" to store all environment variables from the `.env` file. Do not commit the `.env` file directly.
- **File System:**
    - `static/uploads`: Replit's file system is ephemeral for some parts. If uploads need to persist beyond a single session or for longer durations, consider external storage (e.g., cloud bucket) or Replit's database features if applicable. For temporary session-based uploads, the local file system might suffice but will be cleared on repl restart/update.
- **Running the Application:**
    - Configure the `Run` command in `.replit` file to `streamlit run app.py`.
- **MCP Servers:**
    - If MCP servers are Python scripts started as subprocesses (as stdio transport implies), they will run within the same Replit container as the Streamlit app. Paths in `resume_mcp_config.json` should be relative to the project root.
- **Database:**
    - Replit offers a PostgreSQL database. Configure `DATABASE_URL` secret to point to it.
    - Run `init_citation_db()` logic. This could be done by temporarily modifying `app.py` to run it on startup or by using the Replit shell to execute the script snippet.

## VII. Starting the Application and Servers
- **Streamlit App:** `streamlit run app.py`
- **MCP Servers:** The `resume_mcp_config.json` implies these are Python scripts. The `MultiServerMCPClient` will start these as subprocesses if they use `stdio` transport and have `command` and `args` defined. Ensure these scripts are executable and paths are correct.
- **Database:** Ensure PostgreSQL is running and accessible.
- **ClamAV (if used):** Ensure `clamd` is running.

## VIII. Security Considerations (General)
- **Input Validation:** Done by Security Gateway and at each MCP server/tool level.
- **Authentication:** Streamlit app has basic auth. MCP server tools are currently not individually authenticated beyond the gateway concept.
- **Error Handling:** Graceful error display in UI and logging in backend.
- **File Uploads:**
    - Size limits (`MAX_FILE_SIZE_MB`).
    - Extension filtering (`ALLOWED_EXTENSIONS`).
    - (Future) Malware scanning via Security Gateway / ClamAV.
    - (Future) Sanitization of extracted text if displayed directly or used in sensitive contexts.
- **Secrets Management:** Use `.env` file for local, Docker environment variables, or Replit Secrets. Do not hardcode secrets.
- **Database Security:** Strong passwords for DB user, limit network access to DB if possible.
- **Rate Limiting:** Currently a placeholder; implement if exposing any part of this system publicly.

This outline provides a starting point. Specific deployment choices (e.g., cloud provider, Kubernetes vs. Docker Compose) will introduce further considerations.
