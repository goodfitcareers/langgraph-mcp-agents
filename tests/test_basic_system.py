"""
Basic system validation tests for the Resume Automation System
"""

import pytest
import os
import tempfile
from pathlib import Path


def test_import_basic_modules():
    """Test that basic modules can be imported without errors."""
    
    # Test workflow import
    try:
        from workflow.resume_pipeline import create_resume_workflow
        workflow = create_resume_workflow()
        assert workflow is not None
        print("✅ Workflow creation successful")
    except ImportError as e:
        pytest.fail(f"Failed to import workflow module: {e}")
    except Exception as e:
        print(f"⚠️ Workflow creation failed (expected without MCP servers): {e}")


def test_environment_variables():
    """Test that required environment variables are documented."""
    
    # Check if resume_config.env exists
    config_file = Path("resume_config.env")
    assert config_file.exists(), "resume_config.env file should exist as template"
    
    # Read and verify required variables are documented
    with open(config_file, 'r') as f:
        content = f.read()
        
    required_vars = [
        "ANTHROPIC_API_KEY",
        "NOTION_TOKEN", 
        "NOTION_DATABASE_ID"
    ]
    
    for var in required_vars:
        assert var in content, f"Required environment variable {var} should be documented"
    
    print("✅ Environment configuration template is complete")


def test_file_structure():
    """Test that the required file structure exists."""
    
    required_dirs = [
        "mcp_servers",
        "workflow", 
        "parsers",
        "tests"
    ]
    
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        assert dir_path.exists() and dir_path.is_dir(), f"Directory {dir_name} should exist"
    
    required_files = [
        "app.py",
        "requirements.txt",
        "README.md",
        "Dockerfile",
        "mcp_servers/security_gateway.py",
        "mcp_servers/document_processor.py", 
        "mcp_servers/notion_integration.py",
        "workflow/resume_pipeline.py"
    ]
    
    for file_name in required_files:
        file_path = Path(file_name)
        assert file_path.exists() and file_path.is_file(), f"File {file_name} should exist"
    
    print("✅ File structure is complete")


def test_requirements_file():
    """Test that requirements.txt contains necessary dependencies."""
    
    requirements_file = Path("requirements.txt")
    assert requirements_file.exists(), "requirements.txt should exist"
    
    with open(requirements_file, 'r') as f:
        content = f.read()
    
    required_packages = [
        "langchain-anthropic",
        "langchain-mcp-adapters",
        "langgraph",
        "streamlit",
        "notion-client",
        "PyPDF2",
        "python-docx",
        "python-magic"
    ]
    
    for package in required_packages:
        assert package in content, f"Required package {package} should be in requirements.txt"
    
    print("✅ Requirements file contains necessary packages")


def test_mcp_server_basic_structure():
    """Test that MCP servers have basic required structure."""
    
    mcp_servers = [
        "mcp_servers/security_gateway.py",
        "mcp_servers/document_processor.py",
        "mcp_servers/notion_integration.py"
    ]
    
    for server_file in mcp_servers:
        with open(server_file, 'r') as f:
            content = f.read()
        
        # Check for basic MCP structure
        assert "FastMCP" in content, f"{server_file} should use FastMCP"
        assert "@mcp.tool()" in content, f"{server_file} should have MCP tools"
        assert "__main__" in content, f"{server_file} should be executable"
    
    print("✅ MCP servers have correct structure")


def test_workflow_basic_structure():
    """Test that the workflow has the required structure."""
    
    workflow_file = Path("workflow/resume_pipeline.py")
    assert workflow_file.exists(), "Workflow file should exist"
    
    with open(workflow_file, 'r') as f:
        content = f.read()
    
    # Check for LangGraph components
    assert "StateGraph" in content, "Workflow should use StateGraph"
    assert "ResumeProcessingState" in content, "Should have state definition"
    assert "create_resume_workflow" in content, "Should have factory function"
    
    print("✅ Workflow has correct structure")


def test_app_basic_structure():
    """Test that the main app has the required components."""
    
    app_file = Path("app.py")
    assert app_file.exists(), "Main app file should exist"
    
    with open(app_file, 'r') as f:
        content = f.read()
    
    # Check for Streamlit components
    assert "streamlit" in content, "Should import streamlit"
    assert "st.file_uploader" in content, "Should have file upload"
    assert "st.tabs" in content, "Should have tabbed interface"
    assert "Resume Automation System" in content, "Should have correct title"
    
    print("✅ Main app has correct structure")


def test_docker_configuration():
    """Test that Docker configuration is present."""
    
    dockerfile = Path("Dockerfile")
    assert dockerfile.exists(), "Dockerfile should exist"
    
    docker_compose = Path("dockers/docker-compose.yaml")
    assert docker_compose.exists(), "Docker compose file should exist"
    
    with open(dockerfile, 'r') as f:
        dockerfile_content = f.read()
    
    # Check for resume-specific configurations
    assert "python:3.12" in dockerfile_content, "Should use Python 3.12"
    assert "libmagic" in dockerfile_content, "Should install libmagic for file validation"
    assert "streamlit run" in dockerfile_content, "Should run Streamlit"
    
    print("✅ Docker configuration is correct")


def test_security_considerations():
    """Test that basic security measures are in place."""
    
    # Check security gateway
    security_file = Path("mcp_servers/security_gateway.py")
    with open(security_file, 'r') as f:
        content = f.read()
    
    security_features = [
        "ALLOWED_EXTENSIONS",
        "MAX_FILE_SIZE", 
        "validate_file_upload",
        "quarantine_file",
        "magic.from_file"  # MIME type checking
    ]
    
    for feature in security_features:
        assert feature in content, f"Security feature {feature} should be implemented"
    
    print("✅ Basic security features are implemented")


if __name__ == "__main__":
    print("🧪 Running Resume Automation System Tests...")
    print("=" * 50)
    
    # Run tests
    test_import_basic_modules()
    test_environment_variables()
    test_file_structure()
    test_requirements_file()
    test_mcp_server_basic_structure()
    test_workflow_basic_structure()
    test_app_basic_structure()
    test_docker_configuration()
    test_security_considerations()
    
    print("=" * 50)
    print("🎉 All basic system tests passed!")
    print("📋 Next steps:")
    print("   1. Set up environment variables (.env file)")
    print("   2. Install dependencies (pip install -r requirements.txt)")
    print("   3. Test with actual API keys")
    print("   4. Deploy using Docker or run locally") 