"""
Tests for sync status functionality.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from domain.models import Workflow, SyncStatus
from domain.services import WorkflowService, ApplicationService


class TestSyncStatus:
    """Test sync status functionality."""
    
    def test_workflow_sync_status_enum(self):
        """Test that SyncStatus enum values are correct."""
        assert SyncStatus.SYNCED.value == "synced"
        assert SyncStatus.REMOTE_ONLY.value == "remote_only"
        assert SyncStatus.LOCAL_ONLY.value == "local_only"
        assert SyncStatus.UNKNOWN.value == "unknown"
    
    def test_workflow_with_sync_status(self):
        """Test Workflow model with sync status."""
        workflow = Workflow(
            id="test-123",
            name="Test Workflow",
            sync_status=SyncStatus.SYNCED
        )
        assert workflow.sync_status == SyncStatus.SYNCED
    
    def test_local_workflow_detection(self, tmp_path):
        """Test detection of local-only workflows."""
        # Create mock API client and git manager
        mock_api_client = Mock()
        mock_git_manager = Mock()
        
        # Create workflow service with temporary directory
        service = WorkflowService(mock_api_client, mock_git_manager)
        service.workflow_dir = tmp_path / "workflows"
        
        # Create a local workflow directory with metadata
        local_workflow_dir = service.workflow_dir / "local-workflow-123"
        local_workflow_dir.mkdir(parents=True)
        
        metadata = {
            "name": "Local Test Workflow",
            "active": True,
            "tags": ["test", "local"],
            "updatedAt": "2024-01-15T10:30:00Z"
        }
        
        metadata_file = local_workflow_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f)
        
        # Get local workflows
        local_workflows = service._get_local_workflows()
        
        assert len(local_workflows) == 1
        workflow = local_workflows[0]
        assert workflow.id == "local-workflow-123"
        assert workflow.name == "Local Test Workflow"
        assert workflow.sync_status == SyncStatus.LOCAL_ONLY
        assert workflow.active == True
        assert "test" in workflow.tags
    
    def test_merge_remote_and_local_workflows(self, tmp_path):
        """Test merging remote and local workflows with correct sync status."""
        # Create mock API client and git manager
        mock_api_client = Mock()
        mock_git_manager = Mock()
        
        # Create workflow service with temporary directory
        service = WorkflowService(mock_api_client, mock_git_manager)
        service.workflow_dir = tmp_path / "workflows"
        
        # Create remote workflows
        remote_workflows = [
            Workflow(id="remote-only-1", name="Remote Only 1"),
            Workflow(id="synced-1", name="Synced Workflow 1"),
        ]
        
        # Create local workflows
        # 1. Create a synced workflow (exists both locally and remotely)
        synced_dir = service.workflow_dir / "synced-1"
        synced_dir.mkdir(parents=True)
        synced_metadata = {"name": "Synced Workflow 1", "active": True}
        with open(synced_dir / "metadata.json", 'w') as f:
            json.dump(synced_metadata, f)
        
        # 2. Create a local-only workflow
        local_dir = service.workflow_dir / "local-only-1" 
        local_dir.mkdir(parents=True)
        local_metadata = {"name": "Local Only 1", "active": False}
        with open(local_dir / "metadata.json", 'w') as f:
            json.dump(local_metadata, f)
        
        # Merge workflows
        merged = service._merge_remote_and_local_workflows(remote_workflows)
        
        # Verify results
        assert len(merged) == 3
        
        # Find workflows by ID
        workflows_by_id = {w.id: w for w in merged}
        
        # Check remote-only workflow
        remote_only = workflows_by_id["remote-only-1"]
        assert remote_only.sync_status == SyncStatus.REMOTE_ONLY
        
        # Check synced workflow
        synced = workflows_by_id["synced-1"]
        assert synced.sync_status == SyncStatus.SYNCED
        
        # Check local-only workflow
        local_only = workflows_by_id["local-only-1"]
        assert local_only.sync_status == SyncStatus.LOCAL_ONLY
    
    def test_local_workflow_without_metadata(self, tmp_path):
        """Test handling of local workflows without metadata."""
        # Create mock API client and git manager
        mock_api_client = Mock()
        mock_git_manager = Mock()
        
        # Create workflow service with temporary directory
        service = WorkflowService(mock_api_client, mock_git_manager)
        service.workflow_dir = tmp_path / "workflows"
        
        # Create a local workflow directory without metadata
        local_workflow_dir = service.workflow_dir / "no-metadata-123"
        local_workflow_dir.mkdir(parents=True)
        
        # Get local workflows
        local_workflows = service._get_local_workflows()
        
        assert len(local_workflows) == 1
        workflow = local_workflows[0]
        assert workflow.id == "no-metadata-123"
        assert workflow.name == "Local Workflow (no-metadata-123)"
        assert workflow.sync_status == SyncStatus.LOCAL_ONLY
    
    @patch.dict('os.environ', {
        'N8N_DEV_URL': 'https://dev.example.com',
        'N8N_DEV_API_KEY': 'dev-key'
    })
    def test_list_workflows_with_sync_status(self, tmp_path):
        """Test that list_workflows returns workflows with sync status."""
        # Create application service
        app_service = ApplicationService()
        
        # Mock the workflow service
        mock_api_client = Mock()
        mock_git_manager = Mock()
        
        # Mock API response
        mock_api_client.list_workflows.return_value = [
            {
                'id': 'remote-1',
                'name': 'Remote Workflow 1',
                'active': True,
                'tags': [{'name': 'test'}],
                'updatedAt': '2024-01-15T10:30:00Z'
            }
        ]
        
        # Create workflow service
        workflow_service = WorkflowService(mock_api_client, mock_git_manager)
        workflow_service.workflow_dir = tmp_path / "workflows"
        
        # Create a local-only workflow
        local_dir = workflow_service.workflow_dir / "local-only-1"
        local_dir.mkdir(parents=True)
        local_metadata = {"name": "Local Only Workflow", "active": False}
        with open(local_dir / "metadata.json", 'w') as f:
            json.dump(local_metadata, f)
        
        # Test list_workflows
        result = workflow_service.list_workflows()
        
        assert result.success
        workflows = result.data
        assert len(workflows) == 2
        
        # Check that sync status is set
        workflows_by_id = {w.id: w for w in workflows}
        
        remote_workflow = workflows_by_id["remote-1"]
        assert remote_workflow.sync_status == SyncStatus.REMOTE_ONLY
        
        local_workflow = workflows_by_id["local-only-1"]
        assert local_workflow.sync_status == SyncStatus.LOCAL_ONLY