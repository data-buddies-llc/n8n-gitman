"""
Domain models for the n8n workflow manager.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class ValidationStatus(Enum):
    VALID = "valid"
    INVALID = "invalid"
    PARTIAL = "partial"


class EnrichmentStrategy(Enum):
    VERIFY_AND_DISCOVER = "verify_and_discover"
    VERIFY_ONLY = "verify_only"
    DISCOVER_ONLY = "discover_only"
    NO_ENRICHMENT = "no_enrichment"


@dataclass
class Workflow:
    """Represents an n8n workflow."""
    id: str
    name: str
    active: bool = False
    tags: List[str] = None
    updated_at: str = ""
    created_at: str = ""
    nodes: List[Dict[str, Any]] = None
    connections: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.nodes is None:
            self.nodes = []
        if self.connections is None:
            self.connections = {}
    
    @property
    def is_in_repo(self) -> bool:
        """Check if workflow exists in local repository."""
        from pathlib import Path
        import os
        workflow_dir = Path(os.getenv('DEFAULT_WORKFLOW_DIR', 'workflows/devops'))
        return (workflow_dir / self.id).exists()
    
    @property
    def formatted_updated_at(self) -> str:
        """Return formatted update time."""
        if not self.updated_at:
            return ""
        try:
            dt = datetime.fromisoformat(self.updated_at.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M')
        except:
            return self.updated_at


@dataclass
class WorkflowFilter:
    """Filter criteria for workflows."""
    search_term: str = ""
    tags: List[str] = None
    active_only: bool = False
    in_repo_only: bool = False
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class EnvironmentConfig:
    """Configuration for an n8n environment."""
    name: str
    url: str
    api_key: str
    branch: str = ""
    
    def __post_init__(self):
        if not self.branch:
            branch_mapping = {
                'dev': 'dev',
                'testing': 'testing',
                'staging': 'staging',
                'prod': 'main'
            }
            self.branch = branch_mapping.get(self.name, 'main')


@dataclass
class ApplicationState:
    """Current state of the application."""
    current_environment: str
    current_branch: str
    workflows: List[Workflow] = None
    filtered_workflows: List[Workflow] = None
    selected_workflow_index: int = -1
    last_operation: str = ""
    status_message: str = ""
    is_error: bool = False
    
    def __post_init__(self):
        if self.workflows is None:
            self.workflows = []
        if self.filtered_workflows is None:
            self.filtered_workflows = []


@dataclass
class OperationResult:
    """Result of an operation."""
    success: bool
    message: str
    data: Any = None
    error: Exception = None
    
    @classmethod
    def success_result(cls, message: str, data: Any = None) -> 'OperationResult':
        return cls(success=True, message=message, data=data)
    
    @classmethod
    def error_result(cls, message: str, error: Exception = None) -> 'OperationResult':
        return cls(success=False, message=message, error=error)