"""
Reusable UI components for the n8n workflow manager.
"""
from textual.widgets import DataTable, Static
from textual.coordinate import Coordinate
from rich.text import Text
from typing import List, Optional

from domain.models import Workflow, SyncStatus


class WorkflowTable:
    """Wrapper for DataTable to handle workflow-specific operations."""
    
    def __init__(self, table_widget: DataTable):
        self.table = table_widget
        self.workflows: List[Workflow] = []
    
    def setup(self):
        """Initialize the table structure."""
        self.table.add_columns("ID", "Name", "Sync Status", "Active", "Tags", "Modified")
        self.table.cursor_type = "row"
        self.table.can_focus = True
    
    def update_workflows(self, workflows: List[Workflow]):
        """Update the table with new workflow data."""
        self.workflows = workflows
        self.table.clear()
        
        for workflow in workflows:
            active = "✅" if workflow.active else "❌"
            tags = ', '.join(workflow.tags) if workflow.tags else ""
            sync_status = self._get_sync_status_display(workflow.sync_status)
            
            self.table.add_row(
                workflow.id,
                workflow.name,
                sync_status,
                active,
                tags,
                workflow.formatted_updated_at
            )
        
        # Refocus the table after updating
        self.table.focus()
    
    def _get_sync_status_display(self, sync_status: SyncStatus) -> str:
        """Get display string for sync status."""
        status_map = {
            SyncStatus.SYNCED: "🟢 Synced",
            SyncStatus.REMOTE_ONLY: "⬇️ Remote Only", 
            SyncStatus.LOCAL_ONLY: "⬆️ Local Only",
            SyncStatus.UNKNOWN: "❓ Unknown"
        }
        return status_map.get(sync_status, "❓ Unknown")
    
    def get_selected_workflow(self) -> Optional[Workflow]:
        """Get the currently selected workflow."""
        if self.table.cursor_coordinate == Coordinate(-1, -1):
            return None
        
        row_idx = self.table.cursor_coordinate.row
        if row_idx >= len(self.workflows):
            return None
        
        return self.workflows[row_idx]
    
    def get_selected_index(self) -> int:
        """Get the index of the selected workflow."""
        if self.table.cursor_coordinate == Coordinate(-1, -1):
            return -1
        return self.table.cursor_coordinate.row


class StatusDisplay:
    """Wrapper for status message display."""
    
    def __init__(self, status_widget: Static):
        self.widget = status_widget
    
    def update_status(self, message: str, is_error: bool = False):
        """Update the status message."""
        if is_error:
            text = Text(f"❌ {message}", style="bold red")
        else:
            text = Text(f"✅ {message}", style="bold green")
        
        self.widget.update(text)
    
    def clear(self):
        """Clear the status message."""
        self.widget.update("")


class EnvironmentDisplay:
    """Wrapper for environment information display."""
    
    def __init__(self, env_widget: Static, branch_widget: Static):
        self.env_widget = env_widget
        self.branch_widget = branch_widget
    
    def update_environment(self, environment: str):
        """Update the environment display."""
        self.env_widget.update(f"Environment: {environment}")
    
    def update_branch(self, branch: str):
        """Update the branch display."""
        self.branch_widget.update(f"Branch: {branch}")
    
    def update_both(self, environment: str, branch: str):
        """Update both environment and branch displays."""
        self.update_environment(environment)
        self.update_branch(branch)


class GitStatusDisplay:
    """Wrapper for Git status display."""
    
    def __init__(self, git_widget: Static):
        self.git_widget = git_widget
    
    def update_status(self, status: dict):
        """Update Git status display."""
        parts = []
        
        if not status['has_remote']:
            parts.append("No remote")
        elif status['is_synced']:
            parts.append("✓ Synced")
        else:
            if status['is_ahead']:
                parts.append(f"↑{status['ahead_count']}")
            if status['is_behind']:
                parts.append(f"↓{status['behind_count']}")
        
        if status['has_uncommitted']:
            uncommitted_parts = []
            if status['staged_count']:
                uncommitted_parts.append(f"staged: {status['staged_count']}")
            if status['modified_count']:
                uncommitted_parts.append(f"modified: {status['modified_count']}")
            if status['untracked_count']:
                uncommitted_parts.append(f"untracked: {status['untracked_count']}")
            parts.append(f"({', '.join(uncommitted_parts)})")
        
        status_text = "Git: " + " ".join(parts) if parts else "Git: Clean"
        self.git_widget.update(status_text)