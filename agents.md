# Coding Agent Instructions: Resume Automation System (Simplified MVP)

## Project Mission

Transform the `teddynote-lab/langgraph-mcp-agents` template into a specialized resume automation system that processes documents (PDF, DOCX, TXT) and maintains structured professional history databases in Notion with full citation tracking.

## 📋 Key Simplifications for MVP

This is a **simplified version** focusing on core functionality:

✅ **What We're Building:**
- Single-user system (authentication but no multi-tenancy)
- PDF, DOCX, and TXT file processing only
- Single Notion workspace integration
- Claude Sonnet 4 for all AI tasks
- Docker/Replit deployment
- Permanent document storage
- Simple export functionality

❌ **What We're NOT Building (Yet):**
- Audio transcription
- Email processing
- Multi-model optimization
- Complex backup systems
- Multi-tenant support
- Cloud deployment (AWS/GCP)

## 🚀 Quick Start Guide

1. **Clone and Setup** (30 minutes)
   ```bash
   git clone https://github.com/teddynote-lab/langgraph-mcp-agents
   cd langgraph-mcp-agents
   cp .env.example .env
   # Add only ANTHROPIC_API_KEY and NOTION_TOKEN
   ```

2. **Simplify the Template** (2 hours)
   - Remove all MCP servers except document-processor and notion
   - Remove RAG/vector database components
   - Simplify LangGraph to linear workflow
   - Configure for Claude Sonnet 4 only

3. **Build Core Features** (1 week)
   - Add PDF/DOCX/TXT parsers
   - Create resume extraction prompts
   - Build Notion schema mapping
   - Implement basic review UI

4. **Test and Deploy** (3 days)
   - Create synthetic test resumes
   - Test end-to-end flow
   - Dockerize application
   - Deploy to Replit or local Docker

**Total Time to MVP: ~2 weeks**

---

## Starting Point

**Base Template**: https://github.com/teddynote-lab/langgraph-mcp-agents

This template provides:
- ✅ LangGraph + MCP integration
- ✅ Streamlit web interface  
- ✅ Docker deployment setup
- ✅ LangSmith tracing
- ✅ Basic RAG implementation

**Your Task**: Adapt this general-purpose agent system into a specialized resume processing workflow.

---

## Core Requirements

### 1. Document Processing Pipeline

**Replace the generic RAG system with specialized document processors:**

```python
# Current: Generic document loader
# Target: Simplified multi-format resume processor

class DocumentProcessor:
    """
    Support formats (Phase 1):
    - PDF resumes
    - DOCX resumes  
    - TXT files
    """
    
    def classify_document(self, file_path: str) -> DocumentType:
        # Simple file extension based classification
        extension = file_path.lower().split('.')[-1]
        if extension == 'pdf':
            return DocumentType.PDF
        elif extension in ['docx', 'doc']:
            return DocumentType.DOCX
        elif extension in ['txt', 'text']:
            return DocumentType.TEXT
        else:
            raise ValueError(f"Unsupported file type: {extension}")
    
    def extract_structured_data(self, document: Document) -> ProfessionalHistory:
        # Use Claude Sonnet 4 for all extraction
        pass
```

### 2. Notion Database Schema

**Implement the specific schema for professional histories:**

```python
@dataclass
class NotionProfessionalHistorySchema:
    # Required fields
    company: str
    title: str  
    start_year: int
    end_year: Optional[int]
    
    # Detailed role information (stored in page)
    manager_title: Optional[str]
    direct_reports: List[str]
    budget_responsibility: Optional[float]
    headcount: Optional[int]
    quota: Optional[float]
    peer_functions: List[str]
    
    # Extracted content with citations
    achievements: List[Achievement]
    responsibilities: List[str]
    
    # Metadata
    sources: List[Citation]
    confidence_score: float
    last_updated: datetime
```

### 3. Transform MCP Servers

**Current template has generic MCP servers. Create these simplified, focused ones:**

#### A. Document Processing MCP Server
```python
# Location: mcp-servers/document-processor/
# Purpose: Secure document parsing for PDF, DOCX, and TXT files

@mcp.tool()
async def process_resume(document_path: str) -> ExtractedData:
    """
    1. Validate file safety (malware scan)
    2. Detect format (PDF, DOCX, or TXT only)
    3. Parse document content
    4. Use Claude Sonnet 4 to extract structured data
    5. Return with confidence scores and citations
    """

@mcp.tool()
async def extract_text(document_path: str) -> str:
    """
    Simple text extraction from supported formats:
    - PDF: Use PyPDF2 or pdfplumber
    - DOCX: Use python-docx
    - TXT: Direct file read
    """
```

#### B. Notion Integration MCP Server
```python
# Location: mcp-servers/notion-integration/
# Purpose: Manage professional history database

@mcp.tool() 
async def query_existing_roles(client_id: str) -> List[Role]:
    """
    1. Fetch all roles for client from Notion
    2. Include all page properties and content
    3. Cache results for performance
    4. Return structured data
    """

@mcp.tool()
async def update_role_information(
    role_id: str, 
    updates: Dict[str, Any],
    citations: List[Citation]
) -> UpdateResult:
    """
    1. Validate updates against schema
    2. Check for conflicts with existing data
    3. Apply updates with version tracking
    4. Store citations for each field
    5. Trigger backup to S3
    """
```

#### C. Citation Tracking MCP Server
```python
# Location: mcp-servers/citation-tracker/
# Purpose: Maintain source attribution

@mcp.tool()
async def track_extraction(
    source_document: str,
    extracted_fact: str,
    location: DocumentLocation  # page/paragraph/timestamp
) -> CitationId:
    """
    1. Generate unique citation ID
    2. Store in PostgreSQL with full context
    3. Link to specific Notion field
    4. Enable audit trail generation
    """
```

#### D. Security Gateway MCP Server (CRITICAL - BUILD FIRST)
```python
# Location: mcp-servers/security-gateway/
# Purpose: Prevent 45% vulnerability rate found in MCP servers

@mcp.tool()
async def validate_and_forward(
    target_server: str,
    method: str,
    params: Dict[str, Any]
) -> Any:
    """
    1. Input validation (no shell injection)
    2. Authentication check
    3. Rate limiting
    4. Sanitize file paths
    5. Log all requests
    6. Forward to actual MCP server
    7. Sanitize responses
    """
```

### 4. LangGraph Workflow Transformation

**Replace the generic ReAct agent with specialized workflow:**

```python
# Current: Generic agent loop
# Target: Specialized resume processing workflow

class ResumeProcessingWorkflow:
    def __init__(self):
        self.workflow = StateGraph(ResumeProcessingState)
        # ... setup code
    
    # Key nodes to implement:
    
    async def classify_document(self, state: State) -> State:
        """Determine document type and processing strategy"""
        
    async def extract_information(self, state: State) -> State:
        """Extract structured data based on document type"""
        
    async def match_to_existing_roles(self, state: State) -> State:
        """
        Intelligent matching:
        - Fuzzy company name matching
        - Date range overlap detection
        - Title similarity scoring
        - Handle promotions/role changes
        """
        
    async def generate_diff(self, state: State) -> State:
        """
        Create human-readable diff:
        - Group by role
        - Show confidence scores
        - Highlight conflicts
        - Include citations
        """
        
    async def human_review(self, state: State) -> State:
        """
        Implement interrupt pattern:
        - Save checkpoint
        - Present diff in UI
        - Wait for approval
        - Handle edits
        - Resume from checkpoint
        """
```

### 5. State Management Enhancement

```python
class ResumeProcessingState(TypedDict):
    # Workflow identifiers
    workflow_id: str
    client_id: str
    document_id: str
    
    # Processing state
    document_type: DocumentType
    raw_content: str
    extracted_roles: List[ExtractedRole]
    existing_roles: List[NotionRole]
    
    # Matching results
    matched_pairs: List[RoleMatch]
    new_roles: List[ExtractedRole]
    
    # Change tracking
    proposed_changes: List[Change]
    approved_changes: List[Change]
    rejected_changes: List[Change]
    
    # Citations
    citations: Dict[str, Citation]
    
    # Human review
    review_status: ReviewStatus
    reviewer_notes: str
    
    # Metadata
    confidence_scores: Dict[str, float]
    processing_time: float
    error_log: List[str]
```

### 6. UI Transformation (Simplified)

**Current Streamlit interface needs these specific features:**

```python
# main.py - Single page application
def render_app():
    """
    Single page with tabs for different functions:
    1. Upload tab - PDF/DOCX/TXT file upload
    2. Review tab - Approve/reject changes
    3. Database tab - View Notion entries
    4. Export tab - Download data/citations
    """

# components/upload.py
def upload_component():
    """
    - File upload (PDF, DOCX, TXT only)
    - Client name input
    - Process button
    - Status indicator
    """

# components/review.py  
def review_component():
    """
    - Simple diff display
    - Approve/Reject buttons
    - Edit capability
    - Save to Notion button
    """

# components/export.py
def export_component():
    """
    - Export full database as CSV
    - Export citations as JSON
    - Export specific client data
    """
```

---

## Security Requirements (Simplified but Critical)

### Must Implement Before Processing Any Real Data:

1. **File Validation**
   ```python
   # Only accept PDF, DOCX, TXT
   ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.doc', '.txt']
   MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit
   
   def validate_file(file) -> bool:
       # Check extension
       # Check file size
       # Check MIME type matches extension
       # Basic malware scan (use ClamAV or similar)
   ```

2. **Sandboxed Processing**
   ```python
   # Process documents in isolated environment
   # Use Docker container with limited permissions
   # No network access during processing
   # Read-only file system except for specific directories
   ```

3. **Simple Authentication**
   ```python
   # Basic auth for single-user system
   # Can upgrade to multi-user later
   USERNAME = os.environ.get('APP_USERNAME')
   PASSWORD_HASH = os.environ.get('APP_PASSWORD_HASH')
   ```

---

## Implementation Phases (Simplified)

### Phase 1: Core Pipeline (Week 1-2)
- [ ] Fork and set up `teddynote-lab/langgraph-mcp-agents` template
- [ ] Implement Security Gateway MCP Server
- [ ] Create Document Processing MCP for PDF/DOCX/TXT only
- [ ] Set up single Claude Sonnet 4 configuration
- [ ] Implement basic Notion integration (single workspace)
- [ ] Create simple LangGraph workflow

### Phase 2: Essential Features (Week 3)
- [ ] Build human review interface in Streamlit
- [ ] Add citation tracking to PostgreSQL
- [ ] Implement role matching logic
- [ ] Create export functionality
- [ ] Add basic error handling and logging

### Phase 3: Testing & Deployment (Week 4)
- [ ] Security testing with synthetic data
- [ ] End-to-end workflow testing
- [ ] Docker containerization
- [ ] Deploy to Replit or local Docker
- [ ] Documentation and user guide

### Future Enhancements (Post-MVP)
- [ ] Add more document formats (emails, transcripts)
- [ ] Implement model specialization for cost optimization
- [ ] Multi-tenant support
- [ ] Advanced backup strategies
- [ ] Cloud deployment (AWS/GCP)

---

## Testing Requirements

### Unit Tests
```python
# tests/test_document_parser.py
def test_resume_extraction():
    """Test extraction accuracy > 95%"""

def test_role_matching():
    """Test matching precision > 90%"""

def test_security_validation():
    """Test injection prevention"""
```

### Integration Tests
```python
# tests/test_workflow.py
def test_end_to_end_processing():
    """Full workflow with checkpoints"""

def test_human_review_interrupt():
    """Test pause/resume functionality"""
```

### Security Tests
```python
# tests/test_security.py
def test_sql_injection_prevention():
    """Attempt various injections"""

def test_file_path_traversal():
    """Test path validation"""

def test_rate_limiting():
    """Verify rate limits enforced"""
```

---

## Configuration Files to Create

### Simplified Model Strategy (Start with Claude Sonnet 4)

**Phase 1 Approach:**
- Use **Claude Sonnet 4** for all AI tasks initially
- This simplifies development and debugging
- Once pipeline works, optimize by specializing models
- Claude Sonnet 4 excels at both extraction and reasoning

### 1. Environment Configuration
```env
# .env
ANTHROPIC_API_KEY=
NOTION_TOKEN=
LANGSMITH_API_KEY=

# Database
DATABASE_URL=postgresql://user:pass@localhost/resume_db
REDIS_URL=redis://localhost:6379

# Security
JWT_SECRET=
ENCRYPTION_KEY=

# Model Selection (Simplified for Phase 1)
PRIMARY_MODEL=claude-sonnet-4
MODEL_TEMPERATURE=0.2
MAX_TOKENS=8000

# Deployment
ENVIRONMENT=development
PORT=8000

# Storage
UPLOAD_DIR=/app/uploads
PERMANENT_STORAGE=true
```

### 2. MCP Server Configuration
```yaml
# mcp-config.yaml
servers:
  security-gateway:
    transport: stdio
    command: python -m mcp_servers.security_gateway
    
  document-processor:
    transport: http
    url: http://localhost:8001
    auth: bearer
    
  notion-integration:
    transport: http
    url: http://localhost:8002
    auth: bearer
```

---

## Success Criteria (Simplified MVP)

Your implementation is complete when:

1. **Core Functionality**
   - ✅ Processes PDF, DOCX, TXT files successfully
   - ✅ Extracts professional history using Claude Sonnet 4
   - ✅ Updates single Notion workspace
   - ✅ Tracks citations for extracted facts
   - ✅ Human review workflow works

2. **Security Basics**
   - ✅ File validation (type, size, scan)
   - ✅ Basic authentication system
   - ✅ Sandboxed document processing
   - ✅ No direct SQL from user input

3. **Deployment Ready**
   - ✅ Runs in Docker container
   - ✅ Works on Replit
   - ✅ Single `.env` configuration
   - ✅ Basic error handling

4. **Documentation**
   - ✅ README with setup instructions
   - ✅ API documentation
   - ✅ User guide for reviewers

---

## Resources

- **Design Documents**: Refer to "Resume Automation System Blueprint" and "Final Implementation Design"
- **Base Template**: https://github.com/teddynote-lab/langgraph-mcp-agents
- **MCP Documentation**: https://modelcontextprotocol.org
- **LangGraph Guide**: https://langchain-ai.github.io/langgraph/
- **Security Best Practices**: OWASP guidelines for input validation

---

## Project Decisions (Resolved)

1. **Data Retention Policy**: Documents stored permanently in `/app/uploads`
2. **Multi-tenancy**: Single Notion workspace system
3. **Backup Strategy**: Simple export functionality (no automated backups)
4. **Model Selection**: Claude Sonnet 4 for all tasks initially
5. **Deployment Target**: Docker container or Replit
6. **Supported Formats**: PDF, DOCX, and TXT only (Phase 1)

## Simplified Architecture Benefits

By making these decisions, we've reduced complexity by:
- 70% fewer models to configure and test
- 50% less infrastructure (no multi-tenancy)
- 60% fewer document parsers to build
- Single AI provider (Anthropic) for Phase 1
- Simpler deployment with Docker/Replit

This allows focus on:
1. **Core functionality** - Getting the pipeline working end-to-end
2. **Security** - Properly securing the system before adding complexity
3. **User experience** - Making the review interface intuitive
4. **Reliability** - Ensuring the system works consistently

---

## Final Notes

- **Start simple, iterate fast** - Get the core pipeline working first
- **Security is still critical** - Even for a simplified system
- **Use Claude Sonnet 4 everywhere** - Optimize with different models later
- **Test with synthetic resumes** - Create fake resumes for testing
- **Document as you build** - Especially the Notion schema

**Remember**: This simplified approach reduces initial complexity by ~70% while maintaining all core functionality. Once this works reliably, you can add:
- More document types
- Model optimization
- Multi-tenancy
- Advanced features

The goal is a working system in 3-4 weeks, not a perfect system that takes 3 months.
