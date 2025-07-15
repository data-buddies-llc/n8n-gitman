import pytest
import json
from pathlib import Path
from datetime import datetime
from scripts.utils import (
    sanitize_filename,
    create_metadata,
    generate_readme,
    save_workflow,
    load_workflow_metadata,
    find_workflow_file
)


class TestSanitizeFilename:
    def test_basic_sanitization(self):
        assert sanitize_filename("My Workflow") == "my_workflow"
        assert sanitize_filename("Test-Workflow") == "test-workflow"
        assert sanitize_filename("workflow_123") == "workflow_123"
    
    def test_special_characters(self):
        assert sanitize_filename("My Workflow!@#") == "my_workflow"
        assert sanitize_filename("Test$%^&*()") == "test"
        assert sanitize_filename("Hello World!!!") == "hello_world"
    
    def test_multiple_spaces(self):
        assert sanitize_filename("My    Workflow") == "my_workflow"
        assert sanitize_filename("  Test  ") == "test"
    
    def test_max_length(self):
        long_name = "a" * 300
        result = sanitize_filename(long_name)
        assert len(result) == 255
    
    def test_empty_or_invalid(self):
        assert sanitize_filename("") == "workflow"
        assert sanitize_filename("!@#$%^&*()") == "workflow"


class TestCreateMetadata:
    def test_metadata_creation(self):
        metadata = create_metadata("12345", "Test Workflow", "dev")
        
        assert metadata["workflow_id"] == "12345"
        assert metadata["original_name"] == "Test Workflow"
        assert metadata["environment"] == "dev"
        assert "last_pulled" in metadata
        assert metadata["last_pulled"].endswith("Z")


class TestGenerateReadme:
    def test_basic_readme(self):
        workflow_data = {
            "name": "Test Workflow",
            "description": "This is a test workflow"
        }
        metadata = {
            "original_name": "Test Workflow",
            "workflow_id": "12345",
            "environment": "dev",
            "last_pulled": "2024-01-01T12:00:00Z"
        }
        
        readme = generate_readme(workflow_data, metadata)
        
        assert "# Test Workflow" in readme
        assert "**Workflow ID:** 12345" in readme
        assert "**Environment:** dev" in readme
        assert "This is a test workflow" in readme
    
    def test_readme_with_tags_and_nodes(self):
        workflow_data = {
            "name": "Test Workflow",
            "tags": ["automation", "testing"],
            "nodes": [
                {"name": "Start", "type": "n8n-nodes-base.start"},
                {"name": "HTTP Request", "type": "n8n-nodes-base.httpRequest"}
            ]
        }
        metadata = {
            "original_name": "Test Workflow",
            "workflow_id": "12345",
            "environment": "dev",
            "last_pulled": "2024-01-01T12:00:00Z"
        }
        
        readme = generate_readme(workflow_data, metadata)
        
        assert "## Tags" in readme
        assert "- automation" in readme
        assert "- testing" in readme
        assert "## Nodes" in readme
        assert "**Start** (n8n-nodes-base.start)" in readme
        assert "**HTTP Request** (n8n-nodes-base.httpRequest)" in readme


class TestSaveWorkflow:
    def test_save_workflow(self, tmp_path):
        workflow_data = {
            "id": "12345",
            "name": "Test Workflow",
            "description": "Test description",
            "nodes": []
        }
        
        workflow_path = save_workflow(
            workflow_data,
            tmp_path,
            "12345",
            "dev"
        )
        
        assert workflow_path.exists()
        assert (workflow_path / "test_workflow.json").exists()
        assert (workflow_path / "metadata.json").exists()
        assert (workflow_path / "README.md").exists()
        
        with open(workflow_path / "test_workflow.json") as f:
            saved_data = json.load(f)
            assert saved_data["name"] == "Test Workflow"
        
        with open(workflow_path / "metadata.json") as f:
            metadata = json.load(f)
            assert metadata["workflow_id"] == "12345"
            assert metadata["original_name"] == "Test Workflow"
            assert metadata["environment"] == "dev"


class TestLoadWorkflowMetadata:
    def test_load_existing_metadata(self, tmp_path):
        workflow_path = tmp_path / "12345"
        workflow_path.mkdir()
        
        metadata = {
            "workflow_id": "12345",
            "original_name": "Test Workflow",
            "environment": "dev"
        }
        
        with open(workflow_path / "metadata.json", "w") as f:
            json.dump(metadata, f)
        
        loaded = load_workflow_metadata(workflow_path)
        assert loaded == metadata
    
    def test_load_missing_metadata(self, tmp_path):
        workflow_path = tmp_path / "12345"
        workflow_path.mkdir()
        
        loaded = load_workflow_metadata(workflow_path)
        assert loaded is None


class TestFindWorkflowFile:
    def test_find_workflow_file(self, tmp_path):
        workflow_path = tmp_path / "12345"
        workflow_path.mkdir()
        
        workflow_file = workflow_path / "test_workflow.json"
        workflow_file.write_text("{}")
        
        metadata_file = workflow_path / "metadata.json"
        metadata_file.write_text("{}")
        
        found = find_workflow_file(workflow_path)
        assert found == workflow_file
    
    def test_no_workflow_file(self, tmp_path):
        workflow_path = tmp_path / "12345"
        workflow_path.mkdir()
        
        metadata_file = workflow_path / "metadata.json"
        metadata_file.write_text("{}")
        
        found = find_workflow_file(workflow_path)
        assert found is None