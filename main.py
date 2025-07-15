#!/usr/bin/env python3
import os
import sys
import json
import yaml
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
import asyncio

from textual import work
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Static, Button, Input, Label
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer, Grid
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import Screen, ModalScreen
from textual.coordinate import Coordinate
from textual import events

from rich.text import Text
from rich.table import Table

from scripts.api import N8NAPIClient
from scripts.git import GitManager
from scripts.utils import save_workflow, load_workflow_metadata, find_workflow_file, sanitize_filename

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HelpScreen(ModalScreen):
    """Help screen showing keyboard shortcuts."""
    
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Close", show=False),
        Binding("q", "app.pop_screen", "Close", show=False),
        Binding("?", "app.pop_screen", "Close", show=False),
    ]
    
    def compose(self) -> ComposeResult:
        yield Grid(
            Label("🔄 n8n Workflow Manager - Help", id="help-title"),
            Static("""
Navigation:
  ↑/↓        Navigate workflow table
  Tab        Move between UI elements
  /          Focus search box
  
Commands:
  l          List workflows from n8n
  u          Pull selected workflow
  p          Push selected workflow  
  e          Switch environment and branch (if multiple configured)
  b          Show branch information
  r          Refresh workflow list
  q          Quit application
  Ctrl+C     Quit application
  Ctrl+Q     Quit application
  ?          Show this help
  
Mouse:
  Click buttons to perform actions
  Click table rows to select workflows
  
Press ESC or q to close this help
            """, id="help-content"),
            id="help-dialog",
        )


class WorkflowScreen(Screen):
    """Main screen for workflow management."""
    
    def __init__(self, environment: str = None):
        super().__init__()
        self.available_environments = N8NAPIClient.get_available_environments()
        self.environment = environment or os.getenv('DEFAULT_N8N_ENV', 'dev')
        self.api_client = None
        self.git_manager = GitManager()
        self.workflows = []
        self.filtered_workflows = []
        self.workflow_dir = Path(os.getenv('DEFAULT_WORKFLOW_DIR', 'workflows/devops'))
        self.status_message = ""
        self.last_operation = None
        self.environment_switching_enabled = len(self.available_environments) > 1
    
    BINDINGS = [
        Binding("l", "list_workflows", "List", priority=True),
        Binding("u", "pull_workflow", "pUll", priority=True),
        Binding("p", "push_workflow", "Push", priority=True),
        Binding("e", "switch_env", "Env", priority=True),
        Binding("b", "switch_branch", "Branch", priority=True),
        Binding("r", "refresh", "Refresh", priority=True),
        Binding("q", "quit", "Quit", priority=True),
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("ctrl+q", "quit", "Quit", show=False),
        Binding("?", "show_help", "Help", priority=True),
        Binding("f1", "show_help", "Help", show=False),
        Binding("/", "focus_search", "Search", show=False),
        Binding("escape", "app.pop_screen", "Back", show=False),
    ]
        
    def compose(self) -> ComposeResult:
        """Create child widgets for the screen."""
        yield Header()
        yield Container(
            Horizontal(
                Vertical(
                    Static("🔄 n8n Workflow Manager", id="title"),
                    Static(f"Environment: {self.environment}", id="env-status"),
                    Static(f"Branch: {self.git_manager.get_current_branch()}", id="branch-status"),
                    Static("", id="status-message"),
                    id="status-bar"
                ),
                id="top-container"
            ),
            ScrollableContainer(
                Vertical(
                    Horizontal(
                        Label("Search: "),
                        Input(placeholder="Filter workflows...", id="search-input"),
                        id="search-container"
                    ),
                    DataTable(id="workflow-table"),
                    id="main-content"
                ),
                id="scrollable-content"
            ),
            Horizontal(
                Button("List", id="btn-list", variant="primary"),
                Button("Pull", id="btn-pull", variant="success"),
                Button("Push", id="btn-push", variant="warning"),
                Button("Switch Env", id="btn-env", disabled=not self.environment_switching_enabled),
                Button("Switch Branch", id="btn-branch"),
                id="button-container"
            ),
            id="app-container"
        )
        yield Footer()
    
    async def on_mount(self) -> None:
        """Handle mount event."""
        try:
            if self.environment in self.available_environments:
                self.api_client = N8NAPIClient(self.environment)
            else:
                self.api_client = None
                if self.available_environments:
                    self.environment = self.available_environments[0]
                    self.api_client = N8NAPIClient(self.environment)
                    env_status = self.query_one("#env-status", Static)
                    env_status.update(f"Environment: {self.environment}")
                    self.update_status(f"Switched to available environment: {self.environment}")
                else:
                    self.update_status("Demo mode - no API credentials configured", error=True)
        except ValueError as e:
            # Demo mode with sample data if no API config
            self.api_client = None
            self.update_status("Demo mode - no API credentials configured", error=True)
        
        # Switch to the appropriate branch for the current environment
        if self.api_client:
            if self.git_manager.switch_to_environment_branch(self.environment):
                branch_status = self.query_one("#branch-status", Static)
                branch_status.update(f"Branch: {self.git_manager.get_current_branch()}")
            else:
                # This is expected if there are no commits yet
                logger.info(f"Could not switch to {self.environment} branch (likely no commits yet)")
        
        table = self.query_one("#workflow-table", DataTable)
        table.add_columns("ID", "Name", "In Repo", "Active", "Tags", "Modified")
        table.cursor_type = "row"
        table.can_focus = True
        
        if self.api_client:
            self.action_list_workflows()
        else:
            # Load demo data
            await self.load_demo_data()
        
        # Give focus to the table after loading data
        table.focus()
    
    async def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            search_term = event.value.lower()
            self.filter_workflows(search_term)
    
    def filter_workflows(self, search_term: str) -> None:
        """Filter workflows based on search term."""
        if not search_term:
            self.filtered_workflows = self.workflows
        else:
            self.filtered_workflows = [
                w for w in self.workflows
                if search_term in w.get('name', '').lower() or
                search_term in w.get('id', '').lower() or
                self._search_in_tags(w.get('tags', []), search_term)
            ]
        self.update_workflow_table()
    
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
    
    def update_workflow_table(self) -> None:
        """Update the workflow table with current data."""
        table = self.query_one("#workflow-table", DataTable)
        table.clear()
        
        for workflow in self.filtered_workflows:
            workflow_id = workflow.get('id', '')
            name = workflow.get('name', 'Unnamed')
            active = "✅" if workflow.get('active', False) else "❌"
            # Handle tags - they come as objects with 'name' property
            tag_list = workflow.get('tags', [])
            if tag_list and isinstance(tag_list[0], dict):
                tags = ', '.join(tag.get('name', '') for tag in tag_list)
            else:
                tags = ', '.join(tag_list)
            updated_at = workflow.get('updatedAt', '')
            
            workflow_path = self.workflow_dir / workflow_id
            in_repo = "✅" if workflow_path.exists() else "❌"
            
            if updated_at:
                try:
                    dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    updated_at = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
            
            table.add_row(workflow_id, name, in_repo, active, tags, updated_at)
        
        # Refocus the table after updating
        table.focus()
    
    @work(exclusive=True)
    async def action_list_workflows(self) -> None:
        """List workflows from n8n."""
        self.update_status("Fetching workflows...")
        
        try:
            self.workflows = await asyncio.to_thread(self.api_client.list_workflows)
            self.filtered_workflows = self.workflows
            self.update_workflow_table()
            self.update_status(f"Listed {len(self.workflows)} workflows")
            self.last_operation = f"Listed at {datetime.now().strftime('%H:%M:%S')}"
        except Exception as e:
            self.update_status(f"Error: {str(e)}", error=True)
    
    @work(exclusive=True)
    async def action_pull_workflow(self) -> None:
        """Pull selected workflow."""
        table = self.query_one("#workflow-table", DataTable)
        
        if table.cursor_coordinate == Coordinate(-1, -1):
            self.update_status("No workflow selected", error=True)
            return
        
        row_idx = table.cursor_coordinate.row
        if row_idx >= len(self.filtered_workflows):
            return
        
        workflow = self.filtered_workflows[row_idx]
        workflow_id = workflow.get('id')
        workflow_name = workflow.get('name', 'Unnamed')
        
        self.update_status(f"Pulling workflow: {workflow_name}...")
        
        try:
            workflow_data = await asyncio.to_thread(self.api_client.get_workflow, workflow_id)
            
            workflow_path = await asyncio.to_thread(
                save_workflow,
                workflow_data,
                self.workflow_dir,
                workflow_id,
                self.environment
            )
            
            if self.git_manager.auto_commit_workflow_changes(
                workflow_id, workflow_name, "pulled"
            ):
                self.update_status(f"Pulled and committed: {workflow_name}")
            else:
                self.update_status(f"Pulled: {workflow_name}")
            
            self.last_operation = f"Pulled at {datetime.now().strftime('%H:%M:%S')}"
            self.action_list_workflows()
            
        except Exception as e:
            self.update_status(f"Error pulling workflow: {str(e)}", error=True)
    
    @work(exclusive=True)
    async def action_push_workflow(self) -> None:
        """Push selected workflow."""
        table = self.query_one("#workflow-table", DataTable)
        
        if table.cursor_coordinate == Coordinate(-1, -1):
            self.update_status("No workflow selected", error=True)
            return
        
        row_idx = table.cursor_coordinate.row
        if row_idx >= len(self.filtered_workflows):
            return
        
        workflow = self.filtered_workflows[row_idx]
        workflow_id = workflow.get('id')
        workflow_name = workflow.get('name', 'Unnamed')
        
        workflow_path = self.workflow_dir / workflow_id
        if not workflow_path.exists():
            self.update_status(f"Workflow not in repository: {workflow_name}", error=True)
            return
        
        workflow_file = find_workflow_file(workflow_path)
        if not workflow_file:
            self.update_status(f"Workflow file not found: {workflow_name}", error=True)
            return
        
        self.update_status(f"Pushing workflow: {workflow_name}...")
        
        try:
            with open(workflow_file, 'r') as f:
                workflow_data = json.load(f)
            
            updated_workflow = await asyncio.to_thread(
                self.api_client.update_workflow,
                workflow_id,
                workflow_data
            )
            
            self.update_status(f"Pushed: {workflow_name}")
            self.last_operation = f"Pushed at {datetime.now().strftime('%H:%M:%S')}"
            
        except Exception as e:
            self.update_status(f"Error pushing workflow: {str(e)}", error=True)
    
    async def action_switch_env(self) -> None:
        """Switch environment and corresponding git branch."""
        if not self.environment_switching_enabled:
            self.update_status("Environment switching disabled - only one environment configured", error=True)
            return
            
        current_idx = self.available_environments.index(self.environment)
        next_idx = (current_idx + 1) % len(self.available_environments)
        self.environment = self.available_environments[next_idx]
        
        # Switch to the appropriate branch for the new environment
        if self.git_manager.switch_to_environment_branch(self.environment):
            branch_status = self.query_one("#branch-status", Static)
            branch_status.update(f"Branch: {self.git_manager.get_current_branch()}")
            self.update_status(f"Switched to {self.environment} environment and {self.git_manager.get_current_branch()} branch")
        else:
            self.update_status(f"Failed to switch to {self.environment} branch", error=True)
            return
        
        self.api_client.close()
        self.api_client = N8NAPIClient(self.environment)
        
        env_status = self.query_one("#env-status", Static)
        env_status.update(f"Environment: {self.environment}")
        
        self.action_list_workflows()
    
    def update_status(self, message: str, error: bool = False) -> None:
        """Update status message."""
        status = self.query_one("#status-message", Static)
        
        if error:
            text = Text(f"❌ {message}", style="bold red")
        else:
            text = Text(f"✅ {message}", style="bold green")
        
        status.update(text)
    
    async def load_demo_data(self) -> None:
        """Load demo workflow data for demonstration."""
        self.workflows = [
            {
                "id": "demo-001",
                "name": "Customer Onboarding Workflow",
                "active": True,
                "tags": ["automation", "customer"],
                "updatedAt": "2024-01-15T10:30:00Z"
            },
            {
                "id": "demo-002",
                "name": "Daily Report Generator",
                "active": True,
                "tags": ["reporting", "scheduled"],
                "updatedAt": "2024-01-14T09:15:00Z"
            },
            {
                "id": "demo-003",
                "name": "Slack Notification Handler",
                "active": False,
                "tags": ["notifications", "slack"],
                "updatedAt": "2024-01-13T14:45:00Z"
            },
            {
                "id": "demo-004",
                "name": "Database Backup Automation",
                "active": True,
                "tags": ["backup", "database", "devops"],
                "updatedAt": "2024-01-12T22:00:00Z"
            },
            {
                "id": "demo-005",
                "name": "API Health Monitor",
                "active": True,
                "tags": ["monitoring", "api", "devops"],
                "updatedAt": "2024-01-11T16:20:00Z"
            }
        ]
        self.filtered_workflows = self.workflows
        self.update_workflow_table()
        self.update_status("Loaded demo workflows")
    
    def action_show_help(self) -> None:
        """Show help information."""
        self.app.push_screen(HelpScreen())
    
    def action_refresh(self) -> None:
        """Refresh the workflow list."""
        if self.api_client:
            self.action_list_workflows()
        else:
            self.update_status("Cannot refresh in demo mode", error=True)
    
    def action_focus_search(self) -> None:
        """Focus the search input box."""
        search_input = self.query_one("#search-input", Input)
        search_input.focus()
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        
        if button_id == "btn-list":
            if self.api_client:
                self.action_list_workflows()
            else:
                await self.load_demo_data()
        elif button_id == "btn-pull":
            if self.api_client:
                self.action_pull_workflow()
            else:
                self.update_status("Pull disabled in demo mode", error=True)
        elif button_id == "btn-push":
            if self.api_client:
                self.action_push_workflow()
            else:
                self.update_status("Push disabled in demo mode", error=True)
        elif button_id == "btn-env":
            if self.environment_switching_enabled:
                await self.action_switch_env()
            else:
                self.update_status("Environment switching disabled - only one environment configured", error=True)
        elif button_id == "btn-branch":
            branches = self.git_manager.get_branches()
            current = self.git_manager.get_current_branch()
            self.update_status(f"Current branch: {current} | Available: {', '.join(branches)}")


class N8NWorkflowManager(App):
    """n8n Workflow Manager TUI Application."""
    
    CSS = """
    #app-container {
        layout: vertical;
        height: 100%;
    }
    
    #top-container {
        height: 6;
        background: $boost;
        padding: 1;
    }
    
    #status-bar {
        width: 100%;
    }
    
    #title {
        text-style: bold;
        color: $text;
    }
    
    #env-status, #branch-status {
        color: $text-muted;
    }
    
    #status-message {
        margin-top: 1;
    }
    
    #scrollable-content {
        height: 1fr;
    }
    
    #search-container {
        height: 3;
        padding: 1 2;
    }
    
    #search-input {
        width: 50;
    }
    
    #workflow-table {
        width: 100%;
        height: 1fr;
        margin: 0 2;
    }
    
    #button-container {
        height: 3;
        align: center middle;
        padding: 1;
        background: $panel;
    }
    
    Button {
        margin: 0 1;
    }
    
    /* Help Screen Styles */
    #help-dialog {
        grid-size: 1 2;
        grid-gutter: 1 2;
        grid-rows: 1fr 4fr;
        padding: 1 2;
        width: 60;
        height: 25;
        border: thick $primary 60%;
        background: $surface;
    }
    
    #help-title {
        text-style: bold;
        text-align: center;
        color: $text;
        height: 1;
    }
    
    #help-content {
        color: $text;
        background: $surface;
        padding: 1 2;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.load_config()
    
    def load_config(self):
        """Load configuration from file."""
        config_path = Path("config.yaml")
        if config_path.exists():
            with open(config_path) as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {}
    
    def on_mount(self) -> None:
        """Handle app mount."""
        self.push_screen(WorkflowScreen())


def main():
    """Main entry point."""
    app = N8NWorkflowManager()
    app.run()


if __name__ == "__main__":
    main()