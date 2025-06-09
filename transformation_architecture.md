This page outlines the intended final architecture target, we are transforming the original template. 

**🏗️ Architecture Diagrams:**

- **System Overview**: Shows how all components connect, with the security gateway (highlighted in red) protecting your MCP servers
- **Data Flow**: Sequential diagram showing exactly how a document moves through your system
- **LangGraph Workflow**: The complete state machine with human review loops

**🔧 Component Details:**

- **MCP Server Internals**: Detailed architecture for document processing and Notion integration
- **State Management**: How LangGraph persists state across interruptions
- **Security Layers**: Multi-layered security architecture to address the vulnerabilities found in our research

**👤 Human Interaction:**

- **Approval Flow**: State diagram showing all possible paths through the review process
- **Edit Loops**: How changes cycle back for re-review

**🚀 Implementation Guide:**

- **Gantt Chart**: 4-week implementation timeline
- **Project Structure**: Complete file organization
- **Code Templates**: Working examples for both LangGraph workflow and MCP servers

The design incorporates all our research findings:

- ✅ Uses the proven `teddynote-lab/langgraph-mcp-agents` template as foundation
- ✅ Implements security gateway to address the 45% vulnerability rate
- ✅ Includes checkpoint persistence for human-in-the-loop workflows
- ✅ Provides proper citation tracking with PostgreSQL
- ✅ Uses Redis for caching to handle performance requirements

**To start building:**

1. Clone the recommended template
2. Follow the project structure in the design
3. Implement the security gateway first (critical!)
4. Build one MCP server at a time, testing each thoroughly
5. Connect them with the LangGraph workflow

Would you like me to dive deeper into any specific component or help you plan the first implementation sprint?

# Resume Automation System - Final Implementation Design

## 🎯 Executive Summary

This design document provides the complete blueprint for building a resume automation system using MCP servers, LangGraph workflows, and LangSmith monitoring. Based on our technical feasibility research, we've incorporated security hardening, proven patterns, and production-ready templates.

---

## 🏗️ System Architecture Overview

```mermaid
graph TB
    subgraph "Client Layer"
        UI[Web Interface<br/>Streamlit/React]
        API[FastAPI Gateway]
    end

    subgraph "Orchestration Layer"
        LG[LangGraph Workflow Engine]
        LS[LangSmith Monitor]
        CS[Checkpoint Store<br/>PostgreSQL]
    end

    subgraph "MCP Server Layer"
        MCP1[Document Processing<br/>MCP Server]
        MCP2[Notion Integration<br/>MCP Server]
        MCP3[Citation Tracking<br/>MCP Server]
        MCP4[Security Gateway<br/>MCP Server]
    end

    subgraph "Storage Layer"
        PG[(PostgreSQL<br/>State & Citations)]
        REDIS[(Redis<br/>Cache & Queue)]
        S3[S3/MinIO<br/>Document Storage]
        NOTION[(Notion<br/>Database)]
    end

    UI --> API
    API --> LG
    LG --> LS
    LG --> CS
    LG --> MCP4
    MCP4 --> MCP1
    MCP4 --> MCP2
    MCP4 --> MCP3
    MCP1 --> S3
    MCP2 --> NOTION
    MCP3 --> PG
    LG --> REDIS

    style MCP4 fill:#ff9999
    style LS fill:#99ccff

```

---

## 📊 Data Flow Architecture

```mermaid
sequenceDiagram
    participant User
    participant API
    participant LangGraph
    participant DocMCP as Document MCP
    participant NotionMCP as Notion MCP
    participant CiteMCP as Citation MCP
    participant Human as Human Reviewer

    User->>API: Upload Document
    API->>LangGraph: Start Workflow

    LangGraph->>DocMCP: Classify Document
    DocMCP-->>LangGraph: Document Type

    LangGraph->>DocMCP: Extract Information
    DocMCP-->>LangGraph: Structured Data

    LangGraph->>NotionMCP: Query Existing Roles
    NotionMCP-->>LangGraph: Current Database State

    LangGraph->>LangGraph: Match & Deduplicate

    LangGraph->>CiteMCP: Track Sources
    CiteMCP-->>LangGraph: Citation IDs

    LangGraph->>Human: Review Changes
    Human-->>LangGraph: Approve/Reject

    LangGraph->>NotionMCP: Update Database
    NotionMCP-->>LangGraph: Success

    LangGraph->>API: Complete
    API->>User: Show Results

```

---

## 🔄 LangGraph Workflow Design

```mermaid
graph LR
    Start([Start]) --> Ingest[Document<br/>Ingestion]
    Ingest --> Classify{Document<br/>Type?}

    Classify -->|Resume| ResumeParser[Resume<br/>Parser]
    Classify -->|Transcript| TranscriptAnalyzer[Transcript<br/>Analyzer]
    Classify -->|Email/Other| GeneralParser[General<br/>Parser]

    ResumeParser --> Extract[Extract<br/>Role Details]
    TranscriptAnalyzer --> Extract
    GeneralParser --> Extract

    Extract --> Match[Match to<br/>Existing Roles]
    Match --> Enrich[Enrich with<br/>Context]
    Enrich --> Validate[Validate &<br/>Score]

    Validate --> GenDiff[Generate<br/>Diff]
    GenDiff --> Review{Human<br/>Review}

    Review -->|Approved| Update[Update<br/>Notion]
    Review -->|Rejected| Feedback[Log<br/>Feedback]
    Review -->|Needs Edit| Edit[Edit<br/>Changes]

    Edit --> GenDiff
    Update --> Track[Track<br/>Citations]
    Track --> End([End])
    Feedback --> End

    style Review fill:#ffcc99
    style Edit fill:#99ccff

```

---

## 🔧 MCP Server Detailed Architecture

### Document Processing MCP Server

```mermaid
graph TD
    subgraph "Document Processing MCP"
        Input[Document Input] --> Val[Input Validation]
        Val --> Sandbox[Sandboxed Environment]

        Sandbox --> Type{Document Type}
        Type -->|PDF| PDFParser[PDF Parser<br/>PyPDF2/pdfplumber]
        Type -->|DOCX| DOCXParser[DOCX Parser<br/>python-docx]
        Type -->|Image| OCR[OCR Engine<br/>Tesseract/Azure]

        PDFParser --> Struct[Structure<br/>Extraction]
        DOCXParser --> Struct
        OCR --> Struct

        Struct --> NLP[NLP Processing<br/>spaCy/Transformers]
        NLP --> Schema[Schema<br/>Validation]
        Schema --> Output[Structured Output]

        subgraph "Security Layer"
            Val
            Sandbox
        end
    end

```

### Notion Integration MCP Server

```mermaid
graph TD
    subgraph "Notion MCP Server"
        Req[API Request] --> Auth[Authentication<br/>Check]
        Auth --> RL[Rate Limiter]
        RL --> Cache{Cache<br/>Hit?}

        Cache -->|Yes| Return[Return Cached]
        Cache -->|No| Query[Query Builder]

        Query --> Batch[Batch<br/>Processor]
        Batch --> API[Notion API<br/>Call]
        API --> Transform[Data<br/>Transform]
        Transform --> Validate[Schema<br/>Validation]
        Validate --> UpdateCache[Update<br/>Cache]
        UpdateCache --> Return

        subgraph "Error Handling"
            API --> Retry[Retry Logic]
            Retry --> API
            Retry --> Fallback[Fallback]
        end
    end

```

---

## 🗄️ State Management Architecture

```mermaid
graph TD
    subgraph "LangGraph State"
        State[Workflow State] --> Check[Checkpoint<br/>Manager]
        Check --> Store[(PostgreSQL)]

        State --> Memory[In-Memory<br/>State]
        Memory --> Redis[(Redis Cache)]

        subgraph "State Schema"
            Doc[document_id: str]
            Client[client_id: str]
            Roles[extracted_roles: List]
            Changes[pending_changes: Dict]
            Cites[citations: List]
            Status[status: Enum]
        end
    end

    subgraph "Persistence Layer"
        Store --> Backup[S3 Backup]
        Redis --> TTL[TTL Manager]
    end

```

---

## 🔒 Security Architecture

```mermaid
graph TB
    subgraph "Security Layers"
        Input[User Input] --> WAF[Web Application<br/>Firewall]
        WAF --> Auth[Authentication<br/>Layer]
        Auth --> Author[Authorization<br/>Check]
        Author --> Validate[Input<br/>Validation]
        Validate --> Sanitize[Data<br/>Sanitization]
        Sanitize --> Sandbox[Execution<br/>Sandbox]
        Sandbox --> Audit[Audit<br/>Logger]
    end

    subgraph "MCP Security Gateway"
        Gateway[Security Gateway MCP] --> Filter[Request Filter]
        Filter --> Sign[Request Signing]
        Sign --> Encrypt[Encryption Layer]
        Encrypt --> Route[Secure Routing]
    end

    subgraph "Threat Mitigation"
        IDS[Intrusion Detection]
        RateLimit[Rate Limiting]
        IPFilter[IP Filtering]
        Monitoring[Security Monitoring]
    end

    Audit --> Monitoring
    Gateway --> IDS
    Gateway --> RateLimit

```

---

## 👤 Human-in-the-Loop Approval Flow

```mermaid
stateDiagram-v2
    [*] --> Processing: Document Uploaded
    Processing --> DiffGenerated: Extract Complete

    DiffGenerated --> ReviewPending: Generate Diff
    ReviewPending --> InReview: Human Opens

    InReview --> Approved: Accept All
    InReview --> PartialApproved: Accept Some
    InReview --> Rejected: Reject All
    InReview --> EditMode: Request Changes

    EditMode --> DiffRegenerated: Apply Edits
    DiffRegenerated --> ReviewPending: New Diff

    Approved --> Updating: Process Changes
    PartialApproved --> Updating: Process Accepted

    Updating --> Updated: Notion Update Complete
    Updated --> [*]: Workflow Complete

    Rejected --> [*]: No Changes Made

    note right of ReviewPending: Checkpoint saved
    note right of EditMode: State persisted

```

---

## 🚀 Implementation Phases

```mermaid
gantt
    title Implementation Timeline
    dateFormat  YYYY-MM-DD
    section Phase 1 - Foundation
    Environment Setup           :2025-06-10, 3d
    Basic MCP Servers          :3d
    Security Gateway           :2d
    LangGraph Skeleton         :2d

    section Phase 2 - Core Pipeline
    Document Processing MCP    :5d
    Notion Integration MCP     :3d
    Basic Workflow            :3d
    State Management          :2d

    section Phase 3 - Intelligence
    NLP Enhancement           :3d
    Citation Tracking         :2d
    Matching Algorithm        :3d
    Confidence Scoring        :2d

    section Phase 4 - Production
    Human Review UI           :3d
    LangSmith Integration     :2d
    Performance Optimization  :3d
    Security Hardening        :3d
    Deployment               :2d

```

---

## 💻 Key Implementation Files

### Project Structure

```
resume-automation/
├── mcp-servers/
│   ├── document-processor/
│   │   ├── server.py
│   │   ├── parsers/
│   │   ├── extractors/
│   │   └── schemas/
│   ├── notion-integration/
│   │   ├── server.py
│   │   ├── client.py
│   │   └── models/
│   ├── citation-tracker/
│   │   ├── server.py
│   │   └── database/
│   └── security-gateway/
│       ├── server.py
│       └── validators/
├── langgraph/
│   ├── workflow.py
│   ├── nodes/
│   ├── state.py
│   └── checkpoints/
├── api/
│   ├── main.py
│   ├── routes/
│   └── middleware/
├── frontend/
│   ├── streamlit_app.py
│   └── components/
└── infrastructure/
    ├── docker-compose.yml
    ├── kubernetes/
    └── terraform/

```

### Core LangGraph Workflow Implementation

```python
# langgraph/workflow.py
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_mcp_adapters import MultiServerMCPClient

class ResumeProcessingWorkflow:
    def __init__(self):
        self.workflow = StateGraph(ResumeProcessingState)
        self.mcp_client = MultiServerMCPClient([
            "security-gateway",
            "document-processor",
            "notion-integration",
            "citation-tracker"
        ])
        self._build_graph()

    def _build_graph(self):
        # Add nodes
        self.workflow.add_node("ingest", self.ingest_document)
        self.workflow.add_node("classify", self.classify_document)
        self.workflow.add_node("extract", self.extract_information)
        self.workflow.add_node("match", self.match_roles)
        self.workflow.add_node("validate", self.validate_data)
        self.workflow.add_node("diff", self.generate_diff)
        self.workflow.add_node("review", self.human_review)
        self.workflow.add_node("update", self.update_notion)

        # Add edges
        self.workflow.set_entry_point("ingest")
        self.workflow.add_edge("ingest", "classify")
        self.workflow.add_conditional_edges(
            "classify",
            self.route_by_type,
            {
                "resume": "extract",
                "transcript": "extract",
                "other": "extract"
            }
        )
        # ... additional edges

```

### MCP Server Template

```python
# mcp-servers/document-processor/server.py
from fastmcp import FastMCP, Context
from typing import Dict, Any
import sandboxed_execution

mcp = FastMCP("document-processor")

@mcp.tool()
async def process_document(
    ctx: Context,
    document_path: str,
    document_type: str
) -> Dict[str, Any]:
    """Securely process documents with sandboxed execution"""

    # Security validation
    validated_path = await validate_input(document_path)

    # Execute in sandbox
    async with sandboxed_execution.create_sandbox() as sandbox:
        result = await sandbox.run(
            extract_document_data,
            validated_path,
            document_type
        )

    # Track citations
    citation_id = await ctx.call_tool(
        "citation-tracker",
        "track_source",
        source=validated_path,
        extracted_data=result
    )

    return {
        "data": result,
        "citation_id": citation_id,
        "confidence": calculate_confidence(result)
    }

```

---

## 🔍 Monitoring & Observability

```mermaid
graph LR
    subgraph "Metrics Collection"
        App[Application] --> OT[OpenTelemetry]
        OT --> LS[LangSmith]
        OT --> Prom[Prometheus]
        OT --> Logs[Log Aggregator]
    end

    subgraph "Dashboards"
        LS --> Trace[Trace View]
        Prom --> Grafana[Grafana]
        Logs --> Kibana[Kibana]
    end

    subgraph "Alerts"
        Grafana --> Alert[Alert Manager]
        Alert --> Slack[Slack]
        Alert --> PD[PagerDuty]
    end

```

---

## 🎯 Success Metrics

1. **Performance Targets**
    - Document processing: < 2 seconds per page
    - End-to-end workflow: < 30 seconds per document
    - API response time: < 200ms p95
2. **Accuracy Goals**
    - Resume parsing accuracy: > 95%
    - Role matching precision: > 90%
    - Citation accuracy: 100%
3. **Operational Metrics**
    - System uptime: > 99.9%
    - Security incident rate: 0
    - Human review time: < 2 minutes per document

---

## 🚦 Getting Started

1. **Clone the starter template**:
    
    ```bash
    git clone https://github.com/teddynote-lab/langgraph-mcp-agents
    cd langgraph-mcp-agents
    
    ```
    
2. **Set up environment**:
    
    ```bash
    cp .env.example .env
    # Add your API keys and configuration
    docker-compose up -d postgres redis
    
    ```
    
3. **Install dependencies**:
    
    ```bash
    poetry install
    # or
    pip install -r requirements.txt
    
    ```
    
4. **Start development servers**:
    
    ```bash
    # Terminal 1: Start MCP servers
    python -m mcp_servers.security_gateway
    
    # Terminal 2: Start API
    uvicorn api.main:app --reload
    
    # Terminal 3: Start Streamlit UI
    streamlit run frontend/streamlit_app.py
    
    ```
    
5. **Run tests**:
    
    ```bash
    pytest tests/ -v
    
    ```
    

---

## 📝 Next Steps

1. **Security Hardening**: Implement all security layers before processing any real data
2. **Template Customization**: Adapt the teddynote-lab template for your specific schema
3. **Model Selection**: Configure appropriate models for each processing stage
4. **Integration Testing**: Thoroughly test MCP server communication
5. **Performance Baseline**: Establish metrics before optimization

Remember: Start simple, test thoroughly, and iterate based on real usage patterns!
