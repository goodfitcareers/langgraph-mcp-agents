"""
Security Gateway MCP Server - Critical First Component
Provides comprehensive file validation and security checks before processing
"""

import os
import hashlib
import magic
import mcp
from mcp.server.fastmcp import FastMCP
from pathlib import Path
from typing import Dict, Any, List
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security constants
ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.doc', '.txt']
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
UPLOAD_DIR = Path("/app/uploads")
QUARANTINE_DIR = Path("/app/quarantine")

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

# MIME type mappings for validation
EXPECTED_MIME_TYPES = {
    '.pdf': ['application/pdf'],
    '.docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
    '.doc': ['application/msword'],
    '.txt': ['text/plain', 'text/x-plain']
}

# Initialize FastMCP server
mcp = FastMCP(
    "SecurityGateway",
    instructions="Security Gateway for file validation and processing",
    host="localhost",
    port=8001,
)

@mcp.tool()
async def validate_file_upload(file_path: str, file_size: int, client_name: str = "unknown") -> Dict[str, Any]:
    """
    Comprehensive file validation before processing.
    
    Args:
        file_path (str): Path to the uploaded file
        file_size (int): Size of the file in bytes
        client_name (str): Name of the client uploading the file
    
    Returns:
        Dict containing validation results and secure file ID if valid
    """
    
    validation_result = {
        "valid": False,
        "error": "",
        "file_id": "",
        "secure_path": "",
        "warnings": [],
        "validation_timestamp": datetime.now().isoformat()
    }
    
    try:
        # 1. Check if file exists
        if not os.path.exists(file_path):
            validation_result["error"] = f"File not found: {file_path}"
            return validation_result
        
        # 2. Size validation
        actual_size = os.path.getsize(file_path)
        if actual_size != file_size:
            validation_result["error"] = f"File size mismatch: reported {file_size}, actual {actual_size}"
            return validation_result
            
        if file_size > MAX_FILE_SIZE:
            validation_result["error"] = f"File too large: {file_size} bytes (max: {MAX_FILE_SIZE})"
            return validation_result
            
        if file_size == 0:
            validation_result["error"] = "Empty file"
            return validation_result
        
        # 3. Extension validation
        file_ext = Path(file_path).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            validation_result["error"] = f"Invalid file extension: {file_ext}. Allowed: {ALLOWED_EXTENSIONS}"
            return validation_result
        
        # 4. MIME type validation (if python-magic is available)
        try:
            detected_mime = magic.from_file(file_path, mime=True)
            expected_mimes = EXPECTED_MIME_TYPES.get(file_ext, [])
            
            if detected_mime not in expected_mimes:
                validation_result["error"] = f"MIME type mismatch: detected '{detected_mime}', expected one of {expected_mimes}"
                return validation_result
                
        except Exception as e:
            validation_result["warnings"].append(f"MIME type check failed: {str(e)}")
            logger.warning(f"MIME type validation failed for {file_path}: {e}")
        
        # 5. File content basic validation
        try:
            with open(file_path, 'rb') as f:
                header = f.read(1024)  # Read first 1KB
                
                # Basic header validation
                if file_ext == '.pdf' and not header.startswith(b'%PDF-'):
                    validation_result["error"] = "Invalid PDF header"
                    return validation_result
                    
                # Check for suspicious content patterns
                suspicious_patterns = [b'<script', b'javascript:', b'vbscript:', b'data:']
                for pattern in suspicious_patterns:
                    if pattern in header.lower():
                        validation_result["error"] = f"Suspicious content detected: {pattern.decode('utf-8', errors='ignore')}"
                        return validation_result
                        
        except Exception as e:
            validation_result["error"] = f"File content validation failed: {str(e)}"
            return validation_result
        
        # 6. Generate secure file ID and path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        content_hash = _calculate_file_hash(file_path)
        file_id = f"{timestamp}_{content_hash[:12]}_{client_name}"
        
        # Create secure filename
        original_name = Path(file_path).name
        secure_filename = f"{file_id}_{original_name}"
        secure_path = UPLOAD_DIR / secure_filename
        
        validation_result.update({
            "valid": True,
            "file_id": file_id,
            "secure_path": str(secure_path),
            "original_filename": original_name,
            "content_hash": content_hash,
            "detected_mime_type": detected_mime if 'detected_mime' in locals() else "unknown"
        })
        
        logger.info(f"File validation successful: {file_path} -> {file_id}")
        
    except Exception as e:
        validation_result["error"] = f"Validation failed with exception: {str(e)}"
        logger.error(f"File validation exception for {file_path}: {e}")
    
    return validation_result

@mcp.tool()
async def sanitize_and_move_file(source_path: str, secure_path: str, file_id: str) -> Dict[str, Any]:
    """
    Move file to secure processing directory with proper permissions.
    
    Args:
        source_path (str): Original file path
        secure_path (str): Target secure path
        file_id (str): Secure file identifier
    
    Returns:
        Dict containing operation results
    """
    
    result = {
        "success": False,
        "secure_path": "",
        "error": "",
        "moved_timestamp": datetime.now().isoformat()
    }
    
    try:
        source = Path(source_path)
        target = Path(secure_path)
        
        # Ensure target directory exists
        target.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file to secure location (don't move original yet)
        import shutil
        shutil.copy2(source, target)
        
        # Set restrictive permissions (read-only)
        target.chmod(0o444)
        
        # Verify the copy
        if target.exists() and target.stat().st_size == source.stat().st_size:
            result.update({
                "success": True,
                "secure_path": str(target),
                "file_size": target.stat().st_size
            })
            
            logger.info(f"File successfully moved to secure location: {file_id}")
        else:
            result["error"] = "File copy verification failed"
            
    except Exception as e:
        result["error"] = f"File move operation failed: {str(e)}"
        logger.error(f"File move failed for {file_id}: {e}")
    
    return result

@mcp.tool()
async def quarantine_file(file_path: str, reason: str) -> Dict[str, Any]:
    """
    Move suspicious file to quarantine directory.
    
    Args:
        file_path (str): Path to the suspicious file
        reason (str): Reason for quarantine
    
    Returns:
        Dict containing quarantine operation results
    """
    
    result = {
        "quarantined": False,
        "quarantine_path": "",
        "error": ""
    }
    
    try:
        source = Path(file_path)
        if not source.exists():
            result["error"] = "Source file not found"
            return result
        
        # Create quarantine filename with timestamp and reason
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        quarantine_filename = f"QUARANTINE_{timestamp}_{source.name}"
        quarantine_path = QUARANTINE_DIR / quarantine_filename
        
        # Move to quarantine
        import shutil
        shutil.move(str(source), str(quarantine_path))
        
        # Create quarantine metadata file
        metadata_path = quarantine_path.with_suffix('.metadata')
        with open(metadata_path, 'w') as f:
            f.write(f"Quarantine Reason: {reason}\n")
            f.write(f"Original Path: {file_path}\n")
            f.write(f"Quarantine Time: {datetime.now().isoformat()}\n")
        
        result.update({
            "quarantined": True,
            "quarantine_path": str(quarantine_path),
            "metadata_path": str(metadata_path)
        })
        
        logger.warning(f"File quarantined: {file_path} -> {quarantine_path} (Reason: {reason})")
        
    except Exception as e:
        result["error"] = f"Quarantine operation failed: {str(e)}"
        logger.error(f"Quarantine failed for {file_path}: {e}")
    
    return result

@mcp.tool()
async def get_security_status() -> Dict[str, Any]:
    """
    Get current security gateway status and statistics.
    
    Returns:
        Dict containing security status information
    """
    
    try:
        upload_count = len(list(UPLOAD_DIR.glob('*'))) if UPLOAD_DIR.exists() else 0
        quarantine_count = len(list(QUARANTINE_DIR.glob('*.metadata'))) if QUARANTINE_DIR.exists() else 0
        
        return {
            "status": "active",
            "allowed_extensions": ALLOWED_EXTENSIONS,
            "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024),
            "upload_directory": str(UPLOAD_DIR),
            "quarantine_directory": str(QUARANTINE_DIR),
            "files_in_upload": upload_count,
            "files_quarantined": quarantine_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def _calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of file content."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

if __name__ == "__main__":
    logger.info("Starting Security Gateway MCP Server...")
    mcp.run(transport="stdio") 