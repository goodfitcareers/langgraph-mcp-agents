import json
import os
import re
from typing import Any, Dict, Union

from mcp.server import FastMCP, tool

# Configuration
ALLOWED_TARGET_SERVERS = ["document_processor", "notion_integration", "citation_tracker"]
# For MVP, assume uploads are relative to a base directory.
# In a real setup, this would come from a more robust configuration.
BASE_UPLOAD_DIR = "static/uploads"
# Create the directory if it doesn't exist, for local testing.
os.makedirs(BASE_UPLOAD_DIR, exist_ok=True)


mcp = FastMCP(
    name="SecurityGateway",
    description="Validates and (conceptually) forwards requests to other MCP servers. Performs security checks.",
    instructions=(
        "Use this tool to validate requests before they are sent to other internal services. "
        "Specify the target server, the method to call on that server, and the parameters for that method. "
        "If validation is successful, the request can proceed. Otherwise, an error will be returned."
    )
)

@mcp.tool()
async def validate_and_forward(target_server: str, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates a request and, if successful, indicates it's safe to forward to the target server.
    For MVP, actual forwarding is handled by the workflow after this validation.

    Args:
        target_server: The name of the target MCP server (e.g., "document_processor").
        method: The method/tool to be called on the target server.
        params: A dictionary of parameters for the target method.

    Returns:
        A dictionary indicating success and the validated parameters, or an error.
    """
    print(f"[SecurityGateway] Received validation request for target: {target_server}, method: {method}")

    # 1. Input Validation: Target Server
    if not isinstance(target_server, str) or target_server not in ALLOWED_TARGET_SERVERS:
        print(f"[SecurityGateway] Validation failed: Invalid or disallowed target server '{target_server}'.")
        raise ValueError(f"Invalid or disallowed target server: {target_server}. Allowed: {ALLOWED_TARGET_SERVERS}")

    # 2. Input Validation: Method
    if not isinstance(method, str) or not method:
        print(f"[SecurityGateway] Validation failed: Method must be a non-empty string.")
        raise ValueError("Method must be a non-empty string.")

    # 3. Input Validation: Params
    if not isinstance(params, dict):
        print(f"[SecurityGateway] Validation failed: Params must be a dictionary.")
        raise ValueError("Params must be a dictionary.")

    # 4. Input Validation: Document Path (if present)
    if "document_path" in params:
        document_path = params["document_path"]
        if not isinstance(document_path, str):
            print(f"[SecurityGateway] Validation failed: 'document_path' must be a string.")
            raise ValueError("'document_path' must be a string.")

        # Basic path sanitization: Disallow ".."
        if ".." in document_path:
            print(f"[SecurityGateway] Validation failed: Path traversal attempt detected in 'document_path'.")
            raise ValueError("Path traversal attempt detected in 'document_path'.")

        # Ensure the path is within the expected base directory
        # Normalize both paths to prevent issues with separators and relative components
        try:
            # Construct the full, absolute path for the document
            full_document_path = os.path.abspath(os.path.join(BASE_UPLOAD_DIR, document_path))
            # Construct the full, absolute path for the base upload directory
            abs_base_upload_dir = os.path.abspath(BASE_UPLOAD_DIR)

            # Check if the document path is truly within the base upload directory
            if not full_document_path.startswith(abs_base_upload_dir):
                print(f"[SecurityGateway] Validation failed: 'document_path' is outside the allowed directory.")
                raise ValueError("'document_path' is outside the allowed directory.")

            # Additional check: ensure the file actually exists if it's being read
            # This might be more relevant for the document_processor itself, but a basic check here is good.
            # For this validation step, we might only care about the path's structure, not existence.
            # If path is for writing a new file, it might not exist yet.

        except Exception as e: # Catch potential errors from os.path functions
            print(f"[SecurityGateway] Validation failed: Error processing 'document_path': {e}")
            raise ValueError(f"Error processing 'document_path': {e}")

    # 5. Authentication Check (Placeholder for MVP)
    # Example: Check for a simple token if provided
    # if "auth_token" not in params or params["auth_token"] != "SUPER_SECRET_MVP_TOKEN":
    #     print(f"[SecurityGateway] Authentication failed: Missing or invalid auth_token.")
    #     raise ValueError("Authentication failed.")
    print(f"[SecurityGateway] Authentication check passed (MVP placeholder).")


    # 6. Rate Limiting (Placeholder for MVP)
    print(f"[SecurityGateway] Rate limiting check passed (MVP placeholder).")

    # 7. Logging
    print(f"[SecurityGateway] Validation successful for target: {target_server}, method: {method}, params: {json.dumps(params)}")

    # 8. "Forwarding" / Response
    # For MVP, we return a success message. The workflow will make the actual call.
    return {
        "status": "success",
        "message": f"Request for target '{target_server}', method '{method}' validated successfully.",
        "validated_target": target_server,
        "validated_method": method,
        "validated_params": params
    }

if __name__ == "__main__":
    # Ensure the event loop is handled correctly for MCP server
    # FastMCP should handle this internally when mcp.run() is called.
    mcp.run(transport="stdio")
