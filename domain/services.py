"""
Business logic services for the n8n workflow manager.
"""
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

from .models import Workflow, WorkflowFilter, EnvironmentConfig, ApplicationState, OperationResult
from scripts.api import N8NAPIClient
from scripts.git import GitManager
from scripts.utils import save_workflow, find_workflow_file

logger = logging.getLogger(__name__)


class WorkflowService:
    """Service for managing workflow operations."""
    
    def __init__(self, api_client: N8NAPIClient, git_manager: GitManager):
        self.api_client = api_client
        self.git_manager = git_manager
        self.workflow_dir = Path(os.getenv('DEFAULT_WORKFLOW_DIR', 'workflows/devops'))
    
    def list_workflows(self) -> OperationResult:
        """List all workflows from the API."""
        try:
            workflow_data = self.api_client.list_workflows()
            workflows = [self._create_workflow_from_data(data) for data in workflow_data]
            return OperationResult.success_result(
                f"Listed {len(workflows)} workflows", 
                workflows
            )
        except Exception as e:
            logger.error(f"Failed to list workflows: {e}")
            return OperationResult.error_result(f"Error listing workflows: {str(e)}", e)
    
    def pull_workflow(self, workflow: Workflow, environment: str) -> OperationResult:
        """Pull a workflow from the API to local storage."""
        try:
            workflow_data = self.api_client.get_workflow(workflow.id)
            
            workflow_path = save_workflow(
                workflow_data,
                self.workflow_dir,
                workflow.id,
                environment
            )
            
            # Auto-commit changes
            commit_sha = self.git_manager.auto_commit_workflow_changes(
                workflow.id, workflow.name, "pulled"
            )
            
            message = f"Pulled and committed: {workflow.name}" if commit_sha else f"Pulled: {workflow.name}"
            return OperationResult.success_result(message, workflow_path)
            
        except Exception as e:
            logger.error(f"Failed to pull workflow {workflow.id}: {e}")
            return OperationResult.error_result(f"Error pulling workflow: {str(e)}", e)
    
    def push_workflow(self, workflow: Workflow) -> OperationResult:
        """Push a workflow from local storage to the API."""
        try:
            workflow_path = self.workflow_dir / workflow.id
            if not workflow_path.exists():
                return OperationResult.error_result(f"Workflow not in repository: {workflow.name}")
            
            workflow_file = find_workflow_file(workflow_path)
            if not workflow_file:
                return OperationResult.error_result(f"Workflow file not found: {workflow.name}")
            
            with open(workflow_file, 'r') as f:
                workflow_data = json.load(f)
            
            updated_workflow = self.api_client.update_workflow(workflow.id, workflow_data)
            return OperationResult.success_result(f"Pushed: {workflow.name}", updated_workflow)
            
        except Exception as e:
            logger.error(f"Failed to push workflow {workflow.id}: {e}")
            return OperationResult.error_result(f"Error pushing workflow: {str(e)}", e)
    
    def filter_workflows(self, workflows: List[Workflow], filter_criteria: WorkflowFilter) -> List[Workflow]:
        """Filter workflows based on criteria."""
        if not filter_criteria.search_term:
            return workflows
        
        search_term = filter_criteria.search_term.lower()
        
        return [
            w for w in workflows
            if search_term in w.name.lower() or
            search_term in w.id.lower() or
            self._search_in_tags(w.tags, search_term)
        ]
    
    def _search_in_tags(self, tags: List[Any], search_term: str) -> bool:
        """Search for a term in tags, handling both string and object formats."""
        if not tags:
            return False
        
        for tag in tags:
            if isinstance(tag, dict):
                tag_name = tag.get('name', '').lower()
            else:
                tag_name = str(tag).lower()
            
            if search_term in tag_name:
                return True
        
        return False
    
    def _create_workflow_from_data(self, data: Dict[str, Any]) -> Workflow:
        """Create a Workflow model from API data."""
        # Handle tags - they come as objects with 'name' property
        tags = []
        tag_list = data.get('tags', [])
        if tag_list and isinstance(tag_list[0], dict):
            tags = [tag.get('name', '') for tag in tag_list]
        else:
            tags = tag_list
        
        return Workflow(
            id=data.get('id', ''),
            name=data.get('name', 'Unnamed'),
            active=data.get('active', False),
            tags=tags,
            updated_at=data.get('updatedAt', ''),
            created_at=data.get('createdAt', ''),
            nodes=data.get('nodes', []),
            connections=data.get('connections', {})
        )


class EnvironmentService:
    """Service for managing environment operations."""
    
    def __init__(self, git_manager: GitManager):
        self.git_manager = git_manager
    
    def get_available_environments(self) -> List[EnvironmentConfig]:
        """Get list of available environments based on configuration."""
        load_dotenv()
        environments = []
        
        for env_name in ['dev', 'testing', 'staging', 'prod']:
            url = os.getenv(f"N8N_{env_name.upper()}_URL")
            api_key = os.getenv(f"N8N_{env_name.upper()}_API_KEY")
            
            if url and api_key:
                environments.append(EnvironmentConfig(
                    name=env_name,
                    url=url,
                    api_key=api_key
                ))
        
        return environments
    
    def switch_environment(self, environment: str) -> OperationResult:
        """Switch to a different environment and corresponding branch."""
        try:
            if self.git_manager.switch_to_environment_branch(environment):
                current_branch = self.git_manager.get_current_branch()
                return OperationResult.success_result(
                    f"Switched to {environment} environment and {current_branch} branch",
                    {"environment": environment, "branch": current_branch}
                )
            else:
                return OperationResult.error_result(f"Failed to switch to {environment} branch")
        except Exception as e:
            logger.error(f"Failed to switch environment: {e}")
            return OperationResult.error_result(f"Error switching environment: {str(e)}", e)


class ApplicationService:
    """Main application service orchestrating other services."""
    
    def __init__(self):
        self.git_manager = GitManager()
        self.environment_service = EnvironmentService(self.git_manager)
        self.workflow_service = None
        self.api_client = None
        self.state = ApplicationState(
            current_environment="dev",
            current_branch=self.git_manager.get_current_branch()
        )
    
    def initialize(self, environment: str = None) -> OperationResult:
        """Initialize the application with a specific environment."""
        try:
            available_environments = self.environment_service.get_available_environments()
            
            if not available_environments:
                self.state.current_environment = "demo"
                return OperationResult.success_result("Demo mode - no API credentials configured")
            
            # Use provided environment or default to first available
            if environment and environment in [env.name for env in available_environments]:
                self.state.current_environment = environment
            else:
                self.state.current_environment = available_environments[0].name
            
            # Initialize API client
            self.api_client = N8NAPIClient(self.state.current_environment)
            self.workflow_service = WorkflowService(self.api_client, self.git_manager)
            
            # Switch to appropriate branch
            switch_result = self.environment_service.switch_environment(self.state.current_environment)
            if switch_result.success:
                self.state.current_branch = switch_result.data["branch"]
            
            return OperationResult.success_result(f"Initialized with environment: {self.state.current_environment}")
            
        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")
            return OperationResult.error_result(f"Initialization failed: {str(e)}", e)
    
    def get_demo_workflows(self) -> List[Workflow]:
        """Get demo workflows for demonstration purposes."""
        return [
            Workflow(
                id="demo-001",
                name="Customer Onboarding Workflow",
                active=True,
                tags=["automation", "customer"],
                updated_at="2024-01-15T10:30:00Z"
            ),
            Workflow(
                id="demo-002", 
                name="Daily Report Generator",
                active=True,
                tags=["reporting", "scheduled"],
                updated_at="2024-01-14T09:15:00Z"
            ),
            Workflow(
                id="demo-003",
                name="Slack Notification Handler",
                active=False,
                tags=["notifications", "slack"],
                updated_at="2024-01-13T14:45:00Z"
            ),
            Workflow(
                id="demo-004",
                name="Database Backup Automation",
                active=True,
                tags=["backup", "database", "devops"],
                updated_at="2024-01-12T22:00:00Z"
            ),
            Workflow(
                id="demo-005",
                name="API Health Monitor",
                active=True,
                tags=["monitoring", "api", "devops"],
                updated_at="2024-01-11T16:20:00Z"
            )
        ]
    
    def can_switch_environments(self) -> bool:
        """Check if environment switching is available."""
        return len(self.environment_service.get_available_environments()) > 1
    
    def get_branch_info(self) -> str:
        """Get current branch information."""
        branches = self.git_manager.get_branches()
        current = self.git_manager.get_current_branch()
        return f"Current branch: {current} | Available: {', '.join(branches)}"