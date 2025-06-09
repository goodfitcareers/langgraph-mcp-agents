# Resume Automation System 📄

**AI-powered professional history extraction and Notion database management**

[![Python](https://img.shields.io/badge/Python-≥3.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.3.21-green)](https://langchain-ai.github.io/langgraph/)
[![Claude](https://img.shields.io/badge/Claude-Sonnet%204-purple)](https://www.anthropic.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.44+-red)](https://streamlit.io/)
[![Notion](https://img.shields.io/badge/Notion-API-black)](https://developers.notion.com/)

## 🎯 Overview

Transform the way you manage professional histories! This system automatically extracts role information from resumes using Claude Sonnet 4, intelligently matches with existing Notion database entries, and provides human-in-the-loop review before updating your database.

### ✨ Key Features

- **🤖 AI-Powered Extraction**: Claude Sonnet 4 extracts detailed professional roles
- **🔒 Security First**: Comprehensive file validation and malware scanning  
- **🔍 Smart Matching**: Fuzzy matching with existing database entries
- **👀 Human Review**: Approve/reject changes before database updates
- **📊 Full Traceability**: Citation tracking for all extracted information
- **🗃️ Notion Integration**: Seamless database management
- **📁 Multiple Formats**: Support for PDF, DOCX, and TXT files

## 🚀 Quick Start (5 Minutes)

### 1. Clone and Setup

```bash
git clone https://github.com/your-username/resume-automation-system
cd resume-automation-system
```

### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy the example config
cp resume_config.env .env

# Edit .env with your API keys
```

**Required Environment Variables:**

```env
# Anthropic API for Claude Sonnet 4
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Notion Integration
NOTION_TOKEN=secret_your_notion_integration_token
NOTION_DATABASE_ID=your_notion_database_id_here
```

### 4. Run the Application

```bash
streamlit run app.py
```

🎉 **That's it!** Open http://localhost:8501 and start processing resumes.

## 🏗️ System Architecture

```mermaid
graph TB
    subgraph "User Interface"
        UI[Streamlit App]
    end

    subgraph "Security Layer"
        SEC[Security Gateway MCP]
    end

    subgraph "Processing Pipeline"
        DOC[Document Processor MCP]
        CLAUDE[Claude Sonnet 4]
        WORKFLOW[LangGraph Workflow]
    end

    subgraph "Database Layer"
        NOTION[Notion Integration MCP]
        PG[(Citation Database)]
    end

    UI --> SEC
    SEC --> DOC
    DOC --> CLAUDE
    CLAUDE --> WORKFLOW
    WORKFLOW --> NOTION
    WORKFLOW --> PG

    style CLAUDE fill:#99ccff
    style SEC fill:#ff9999
    style WORKFLOW fill:#99ff99
```

## 📋 How It Works

### 1. Upload Resume 📤
- Drag and drop PDF, DOCX, or TXT files
- Automatic file validation and security scanning
- File size limit: 10MB

### 2. AI Extraction 🤖
- Claude Sonnet 4 analyzes the document
- Extracts professional roles with detailed information:
  - Company names and job titles
  - Employment dates and duration
  - Achievements and responsibilities
  - Manager information and team details
  - Budget/quota responsibilities

### 3. Smart Matching 🔍
- Fuzzy matching with existing Notion database
- Identifies potential duplicates and updates
- Confidence scoring for all matches

### 4. Human Review 👀
- Clear diff view of proposed changes
- Individual approval for each change
- Confidence scores and source citations
- Edit capabilities before final approval

### 5. Database Update 💾
- Approved changes saved to Notion
- Full citation tracking
- Automatic backup and versioning

## 🛡️ Security Features

- **File Type Validation**: Only PDF, DOCX, TXT allowed
- **Size Limits**: 10MB maximum file size
- **MIME Type Checking**: Validates file headers
- **Malware Scanning**: Basic pattern detection
- **Sandboxed Processing**: Isolated execution environment
- **Secure File Handling**: Automatic cleanup and quarantine
- **Input Sanitization**: SQL injection prevention
- **Authentication**: Optional login system

## 📊 Notion Database Schema

Your Notion database should have these properties:

| Property | Type | Description |
|----------|------|-------------|
| Client | Title | Resume owner's name |
| Company | Text | Company/organization name |
| Title | Text | Job title/position |
| Start Year | Number | Year employment started |
| End Year | Number | Year employment ended (null if current) |
| Start Month | Number | Month employment started (1-12) |
| End Month | Number | Month employment ended (1-12) |
| Manager Title | Text | Direct manager's title |
| Headcount | Number | Team size managed |
| Budget Responsibility | Number | Budget managed (USD) |
| Quota | Number | Sales/revenue quota (USD) |
| Location | Text | Work location |
| Employment Type | Select | full-time, part-time, contract, etc. |

## 🐳 Docker Deployment

### Quick Deploy with Docker

```bash
# Build and run
docker-compose up -d

# Access at http://localhost:8000
```

### Docker Configuration

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./uploads:/app/uploads
```

## 🧪 Testing

### Run Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest tests/ -v

# Run specific test categories
pytest tests/test_security.py -v  # Security tests
pytest tests/test_integration.py -v  # Integration tests
```

### Test Coverage

- **Security Validation**: File type, size, malware detection
- **Document Processing**: PDF, DOCX, TXT extraction
- **AI Extraction**: Role identification and structuring
- **Database Operations**: Notion CRUD operations
- **Workflow Integration**: End-to-end pipeline testing

## 📈 Performance & Limits

### Processing Times
- **Small Resume** (1-2 pages): 15-30 seconds
- **Large Resume** (3-5 pages): 30-60 seconds
- **Complex Resume** (multiple roles): 60-90 seconds

### Rate Limits
- **Anthropic API**: Respects standard rate limits
- **Notion API**: 3 requests per second
- **File Processing**: 10MB max file size

### Scaling Considerations
- Current setup: Single-user, local processing
- For scale: Consider Redis caching, worker queues
- Database: PostgreSQL for citation storage

## 🔧 Configuration Options

### Environment Variables

```env
# Core Configuration
ANTHROPIC_API_KEY=required
NOTION_TOKEN=required
NOTION_DATABASE_ID=required

# Optional Features
USE_LOGIN=false
LANGSMITH_TRACING=false
DEBUG=true

# File Processing
MAX_FILE_SIZE_MB=10
UPLOAD_DIR=/app/uploads
QUARANTINE_DIR=/app/quarantine

# Database
DATABASE_URL=postgresql://user:pass@localhost/resume_db
```

### Customization

- **Prompts**: Modify extraction prompts in `mcp_servers/document_processor.py`
- **Security**: Adjust validation rules in `mcp_servers/security_gateway.py`
- **UI**: Customize interface in `app.py`
- **Schema**: Modify Notion schema mapping in `mcp_servers/notion_integration.py`

## 🚧 Roadmap

### Phase 1: MVP (Current)
- ✅ Basic file processing (PDF, DOCX, TXT)
- ✅ Claude Sonnet 4 integration
- ✅ Human review workflow
- ✅ Notion database integration
- ✅ Security validation

### Phase 2: Enhanced Features
- [ ] Audio transcription support
- [ ] Email processing
- [ ] Advanced citation tracking
- [ ] Batch processing
- [ ] API endpoints

### Phase 3: Scale & Performance
- [ ] Multi-user support
- [ ] Cloud deployment (AWS/GCP)
- [ ] Advanced caching
- [ ] Model optimization
- [ ] Analytics dashboard

## 🐛 Troubleshooting

### Common Issues

**1. "Anthropic API key not found"**
```bash
# Check your .env file
cat .env | grep ANTHROPIC_API_KEY
```

**2. "Notion database not accessible"**
```bash
# Verify database ID and token
# Check Notion integration permissions
```

**3. "File processing failed"**
```bash
# Check file format (PDF, DOCX, TXT only)
# Verify file size (<10MB)
# Check server logs for details
```

**4. "MCP server connection failed"**
```bash
# Restart the application
# Check Python environment and dependencies
```

### Debug Mode

```bash
# Run with debug logging
DEBUG=true streamlit run app.py

# Check MCP server logs
python mcp_servers/security_gateway.py

# Test individual components
pytest tests/test_document_processor.py -v -s
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone and setup development environment
git clone https://github.com/your-username/resume-automation-system
cd resume-automation-system

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Format code
black .
isort .
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **LangChain & LangGraph**: Workflow orchestration
- **Anthropic**: Claude Sonnet 4 AI model
- **Notion**: Database platform
- **Streamlit**: Web interface framework
- **MCP Protocol**: Model Context Protocol

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-username/resume-automation-system/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/resume-automation-system/discussions)
- **Documentation**: [Wiki](https://github.com/your-username/resume-automation-system/wiki)

---

<div align="center">

**Made with ❤️ and AI**

[Report Bug](https://github.com/your-username/resume-automation-system/issues) • [Request Feature](https://github.com/your-username/resume-automation-system/issues) • [Documentation](https://github.com/your-username/resume-automation-system/wiki)

</div>
