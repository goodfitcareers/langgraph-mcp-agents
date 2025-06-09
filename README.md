# Resume Automation System (MVP)

This project transforms the original LangGraph MCP template into a simplified resume processing pipeline. It parses PDF, DOCX and TXT files, extracts professional history using Claude Sonnet 4 and stores results in a Notion workspace with citation tracking.

## Quick Start (5 Minutes)

```bash
# 1. Clone the repository
git clone https://github.com/your-fork/resume-automation-mvp
cd resume-automation-mvp

# 2. Add credentials
cp .env.example .env
# edit .env and fill ANTHROPIC_API_KEY and NOTION_TOKEN

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the Streamlit app
streamlit run app.py
```

Upload a resume on the web interface to start processing.

## MCP Servers
- **security-gateway** – validates and forwards requests
- **document-processor** – parses documents and extracts text
- **notion-integration** – reads/writes the Notion database
- **citation-tracker** – stores source citations

Server commands are configured in `mcp-config.yaml`.

## Environment Variables
See `.env.example` for all configuration options.


