import os
import json
import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, TypedDict, Union

from dotenv import load_dotenv
from mcp.server import FastMCP, tool

# Attempt to import parsers and handle potential ImportError
try:
    from parsers.file_parser import (
        extract_text_from_pdf,
        extract_text_from_docx,
        extract_text_from_txt,
        FileParserError
    )
except ImportError:
    # This will allow the MCP server to start and potentially offer other tools,
    # but text extraction related tools will fail if parsers are missing.
    # Or, you could choose to raise an error here to prevent startup without parsers.
    print("CRITICAL: Could not import file parsers from parsers.file_parser. Text extraction tools will fail.")
    extract_text_from_pdf = None
    extract_text_from_docx = None
    extract_text_from_txt = None
    FileParserError = Exception # Fallback to generic Exception if FileParserError is not available

# Attempt to import Anthropic client
try:
    import anthropic
except ImportError:
    anthropic = None
    print("CRITICAL: anthropic library not found. LLM-based extraction will not be available.")


# Load environment variables
load_dotenv(override=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "claude-3-5-sonnet-20240620") # Default if not set
MAX_FILE_SIZE_MB_ENV = os.getenv("MAX_FILE_SIZE_MB", "10")
ALLOWED_EXTENSIONS_ENV = os.getenv("ALLOWED_EXTENSIONS", ".pdf,.docx,.doc,.txt")

# Initialize Anthropic Client
anthropic_client = None
if anthropic and ANTHROPIC_API_KEY:
    try:
        anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    except Exception as e:
        print(f"Error initializing Anthropic client: {e}")
        anthropic_client = None
elif not anthropic:
    print("Anthropic library not installed, LLM features disabled.")
elif not ANTHROPIC_API_KEY:
    print("ANTHROPIC_API_KEY not found in environment variables, LLM features disabled.")


# --- Type Definitions ---

class DocumentType(Enum):
    PDF = ".pdf"
    DOCX = ".docx"
    DOC = ".doc" # .doc often handled by python-docx or requires antiword/libreoffice
    TEXT = ".txt"
    UNSUPPORTED = "unsupported"

class ProfessionalHistory(TypedDict, total=False): # total=False makes all fields optional initially
    company: str
    title: str
    start_year: Optional[int]
    end_year: Optional[int] # Can be "Present" or an int
    manager_title: Optional[str]
    direct_reports: Optional[int]
    budget_responsibility: Optional[str] # e.g., "$1M", "None"
    headcount: Optional[int]
    quota: Optional[str] # e.g., "$500k ARR"
    peer_functions: Optional[List[str]]
    achievements: List[str]
    responsibilities: List[str]
    # For later:
    # sources: Optional[List[str]]
    # confidence_score: Optional[float]
    # last_updated: Optional[str]

class ExtractedData(TypedDict):
    professional_history: List[ProfessionalHistory]
    raw_text_summary: Optional[str] # Or full raw_text if preferred
    confidence_score: Optional[float] # Overall confidence for the extraction
    errors: Optional[List[str]]


# --- MCP Server Definition ---
mcp = FastMCP(
    name="DocumentProcessor",
    description="Parses documents (PDF, DOCX, TXT) and extracts structured professional history using an LLM.",
    instructions=(
        "Provide a file path to a resume/CV. The server will attempt to parse it, "
        "extract raw text, and then use an LLM to structure professional history details."
    )
)

# --- Helper Functions ---
def classify_document(file_path: str) -> DocumentType:
    """Determines document type based on file extension."""
    if not isinstance(file_path, str):
        return DocumentType.UNSUPPORTED
    _, ext = os.path.splitext(file_path.lower())
    if ext == ".pdf":
        return DocumentType.PDF
    elif ext == ".docx":
        return DocumentType.DOCX
    elif ext == ".doc":
        # python-docx can sometimes handle .doc, but it's less reliable.
        # For true .doc, other tools like antiword or LibreOffice might be needed.
        # For MVP, we'll treat it like docx for now, or mark as special handling.
        return DocumentType.DOC # Or DocumentType.DOCX if assuming python-docx handles it
    elif ext == ".txt":
        return DocumentType.TEXT
    else:
        return DocumentType.UNSUPPORTED

# --- MCP Tools ---

@mcp.tool()
async def extract_text(file_path: str) -> Dict[str, Any]:
    """
    Extracts raw text content from a given document file.
    Relies on the Security Gateway for path validation if called through it.
    """
    print(f"[DocumentProcessor] Received extract_text request for: {file_path}")
    if not isinstance(file_path, str):
        return {"error": "File path must be a string."}
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}

    doc_type = classify_document(file_path)
    extracted_text = ""
    error_message = None

    try:
        if doc_type == DocumentType.PDF:
            if extract_text_from_pdf:
                extracted_text = extract_text_from_pdf(file_path)
            else:
                raise RuntimeError("PDF parser (extract_text_from_pdf) is not available.")
        elif doc_type == DocumentType.DOCX or doc_type == DocumentType.DOC: # Assuming .doc can be handled by docx parser
            if extract_text_from_docx:
                extracted_text = extract_text_from_docx(file_path)
            else:
                raise RuntimeError("DOCX parser (extract_text_from_docx) is not available.")
        elif doc_type == DocumentType.TEXT:
            if extract_text_from_txt:
                extracted_text = extract_text_from_txt(file_path)
            else:
                raise RuntimeError("TXT parser (extract_text_from_txt) is not available.")
        else:
            raise ValueError(f"Unsupported document type: {doc_type.value} for file {file_path}")

        print(f"[DocumentProcessor] Text extracted successfully from {file_path} (type: {doc_type.name}). Length: {len(extracted_text)}")
        return {"extracted_text": extracted_text, "document_type": doc_type.name, "status": "success"}

    except FileParserError as e:
        error_message = f"File parsing error for '{file_path}': {e}"
    except ValueError as e:
        error_message = str(e)
    except RuntimeError as e: # For missing parsers
        error_message = str(e)
    except Exception as e:
        error_message = f"An unexpected error occurred during text extraction for '{file_path}': {e}"

    print(f"[DocumentProcessor] Error in extract_text: {error_message}")
    return {"error": error_message, "status": "failure"}


@mcp.tool()
async def process_resume(document_path: str, client_id: Optional[str] = None) -> ExtractedData:
    """
    Processes a resume document to extract structured professional history.
    `client_id` is optional and reserved for future use (e.g., context, personalization).
    """
    print(f"[DocumentProcessor] Received process_resume request for: {document_path}, client_id: {client_id}")

    # 1. File Validation (Basic)
    if not isinstance(document_path, str):
        return ExtractedData(professional_history=[], raw_text_summary=None, confidence_score=0.0, errors=["Invalid document path type."])
    if not os.path.exists(document_path):
        return ExtractedData(professional_history=[], raw_text_summary=None, confidence_score=0.0, errors=[f"File not found: {document_path}"])

    doc_type = classify_document(document_path)
    allowed_extensions = [ext.strip() for ext in ALLOWED_EXTENSIONS_ENV.split(',')]
    file_ext = os.path.splitext(document_path.lower())[1]

    if doc_type == DocumentType.UNSUPPORTED or file_ext not in allowed_extensions:
        return ExtractedData(professional_history=[], raw_text_summary=None, confidence_score=0.0, errors=[f"Unsupported document type or extension: {file_ext}"])

    try:
        max_size_bytes = int(MAX_FILE_SIZE_MB_ENV) * 1024 * 1024
        if os.path.getsize(document_path) > max_size_bytes:
            return ExtractedData(professional_history=[], raw_text_summary=None, confidence_score=0.0, errors=[f"File size exceeds {MAX_FILE_SIZE_MB_ENV}MB limit."])
    except ValueError:
         return ExtractedData(professional_history=[], raw_text_summary=None, confidence_score=0.0, errors=["Invalid MAX_FILE_SIZE_MB configuration."])


    # 2. Parse Document Content (using the local extract_text tool)
    extraction_result = await extract_text(file_path=document_path)
    if extraction_result.get("status") == "failure" or "error" in extraction_result:
        error_msg = extraction_result.get('error', 'Unknown error during text extraction.')
        return ExtractedData(professional_history=[], raw_text_summary=None, confidence_score=0.0, errors=[error_msg])

    raw_text = extraction_result.get("extracted_text", "")
    if not raw_text.strip():
        return ExtractedData(professional_history=[], raw_text_summary="", confidence_score=0.0, errors=["No text content extracted from the document."])

    # 3. Use Claude Sonnet for Extraction
    if not anthropic_client:
        return ExtractedData(professional_history=[], raw_text_summary=raw_text[:500], confidence_score=0.0, errors=["Anthropic client not available. LLM extraction skipped."])

    prompt = f"""
        You are an expert resume parser. Analyze the following resume text and extract the professional history.
        For each role, provide the following details if available:
        - company: Name of the company.
        - title: Job title.
        - start_year: The year the role started (integer).
        - end_year: The year the role ended (integer, or "Present" if current).
        - manager_title: Title of the person this role reported to.
        - direct_reports: Number of direct reports (integer).
        - budget_responsibility: Description of budget managed (e.g., "$1M", "Team budget").
        - headcount: Total team size managed (integer).
        - quota: Sales quota if applicable (e.g., "$500k ARR").
        - peer_functions: List of peer functions or departments collaborated with (list of strings).
        - achievements: Key achievements in this role (list of strings, each achievement as a separate string).
        - responsibilities: Main responsibilities in this role (list of strings, each responsibility as a separate string).

        If a detail is not present, omit the key or set its value to null where appropriate for the type.
        Focus on clear, factual extraction. Achievements and responsibilities should be concise bullet points or short sentences.
        Format the output as a JSON list of objects, where each object represents one professional role.
        Example:
        [
          {{
            "company": "Tech Solutions Inc.",
            "title": "Software Engineer",
            "start_year": 2018,
            "end_year": 2020,
            "achievements": ["Developed feature X, resulting in Y% improvement.", "Led a small project team."],
            "responsibilities": ["Wrote and tested code.", "Collaborated with product managers."]
          }},
          {{
            "company": "Innovate Corp.",
            "title": "Senior Software Engineer",
            "start_year": 2020,
            "end_year": "Present",
            "manager_title": "Engineering Manager",
            "direct_reports": 3,
            "achievements": ["Designed system Z.", "Mentored junior engineers."],
            "responsibilities": ["Lead development of new platform.", "Architect scalable solutions."]
          }}
        ]

        Here is the resume text:
        ---
        {raw_text}
        ---
    """

    extracted_roles: List[ProfessionalHistory] = []
    llm_errors = []

    try:
        print(f"[DocumentProcessor] Sending request to Anthropic API (model: {PRIMARY_MODEL}). Text length: {len(raw_text)}")
        response = anthropic_client.messages.create(
            model=PRIMARY_MODEL,
            max_tokens=4000, # Adjust as needed, ensure it's enough for typical resume outputs
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # The response content is a list of blocks; we expect one 'text' block.
        llm_response_text = ""
        if response.content and isinstance(response.content, list):
            for block in response.content:
                if hasattr(block, 'text'):
                    llm_response_text += block.text

        print(f"[DocumentProcessor] Received response from Anthropic API. Attempting to parse JSON.")
        # LLM might return JSON within triple backticks or just raw JSON
        if llm_response_text.strip().startswith("```json"):
            llm_response_text = llm_response_text.strip()[7:-3].strip() # Remove ```json ... ```
        elif llm_response_text.strip().startswith("```"):
             llm_response_text = llm_response_text.strip()[3:-3].strip() # Remove ``` ... ```

        parsed_llm_output = json.loads(llm_response_text)

        if isinstance(parsed_llm_output, list):
            for role_data in parsed_llm_output:
                if isinstance(role_data, dict):
                    # Basic type checking/conversion for critical fields
                    if "start_year" in role_data and isinstance(role_data["start_year"], str):
                        try:
                            role_data["start_year"] = int(role_data["start_year"])
                        except ValueError:
                            pass # Keep as string if not convertible, or handle error
                    if "end_year" in role_data and isinstance(role_data["end_year"], str) and role_data["end_year"].lower() != "present":
                        try:
                            role_data["end_year"] = int(role_data["end_year"])
                        except ValueError:
                            pass

                    # Ensure achievements and responsibilities are lists of strings
                    for key in ["achievements", "responsibilities", "peer_functions"]:
                        if key in role_data and not (isinstance(role_data[key], list) and all(isinstance(item, str) for item in role_data[key])):
                            # Attempt to fix if it's a single string, or list of non-strings
                            if isinstance(role_data[key], str):
                                role_data[key] = [role_data[key]]
                            else: # If it's a list of something else, or other type, mark as problematic or clear
                                print(f"[DocumentProcessor] Warning: Field '{key}' for company '{role_data.get('company')}' is not a list of strings. Clearing.")
                                role_data[key] = []


                    # Cast to ProfessionalHistory TypedDict.
                    # This doesn't enforce types at runtime but helps with static analysis.
                    # For stricter validation, a library like Pydantic would be used.
                    extracted_roles.append(ProfessionalHistory(**{k: v for k, v in role_data.items() if k in ProfessionalHistory.__annotations__}))
                else:
                    llm_errors.append(f"LLM returned a list item that is not a dictionary: {role_data}")
        else:
            llm_errors.append("LLM response was not a JSON list as expected.")
            print(f"[DocumentProcessor] LLM response was not a list: {llm_response_text}")

    except json.JSONDecodeError as e:
        llm_errors.append(f"Failed to parse LLM JSON response: {e}. Response was: {llm_response_text[:500]}...")
        print(f"[DocumentProcessor] JSONDecodeError: {e}. Raw LLM response snippet: {llm_response_text[:500]}")
    except Exception as e:
        llm_errors.append(f"Error interacting with LLM or processing its response: {e}")
        print(f"[DocumentProcessor] Exception during LLM interaction: {e}")

    # 4. Return with Confidence (Placeholder)
    # For MVP, confidence is fixed. Raw text summary is first 500 chars.
    summary = raw_text[:500] + "..." if len(raw_text) > 500 else raw_text

    final_data = ExtractedData(
        professional_history=extracted_roles,
        raw_text_summary=summary,
        confidence_score=0.9 if extracted_roles and not llm_errors else 0.5, # Basic confidence
        errors=llm_errors if llm_errors else None
    )

    if llm_errors:
        print(f"[DocumentProcessor] Finished process_resume for {document_path} with errors: {llm_errors}")
    else:
        print(f"[DocumentProcessor] Finished process_resume for {document_path} successfully. Extracted {len(extracted_roles)} roles.")

    return final_data


if __name__ == "__main__":
    print("Document Processor MCP Server starting...")
    # Example of how to test locally (requires manual file creation or modification)
    # This is illustrative; actual testing would involve calling the tools.
    # For instance, you might have a dummy_resume.txt in a test_data directory.

    # test_file_path = "test_data/dummy_resume.txt"
    # if not os.path.exists("test_data"):
    #     os.makedirs("test_data", exist_ok=True)
    # if not os.path.exists(test_file_path):
    #     with open(test_file_path, "w") as f:
    #         f.write("Sample resume text for John Doe, worked at Acme Corp as Engineer from 2019 to 2022.")
    #
    # async def run_test():
    #     print("Testing extract_text tool...")
    #     result_text = await extract_text(file_path=test_file_path)
    #     print(f"extract_text result: {result_text}")
    #
    #     if anthropic_client and result_text.get("status") == "success":
    #         print("\nTesting process_resume tool...")
    #         result_process = await process_resume(document_path=test_file_path)
    #         print(f"process_resume result: {json.dumps(result_process, indent=2)}")
    #     else:
    #         print("\nSkipping process_resume test due to missing Anthropic client or text extraction failure.")

    # if os.getenv("ANTHROPIC_API_KEY"):
    #    import asyncio
    #    asyncio.run(run_test())
    # else:
    #    print("ANTHROPIC_API_KEY not set. Skipping local tool tests that require LLM.")

    mcp.run(transport="stdio")
