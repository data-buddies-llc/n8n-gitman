"""
Screen components for the n8n workflow manager.
"""
from textual import work
from textual.app import ComposeResult
from textual.widgets import Header, Footer, DataTable, Static, Button, Input, Label
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer, Grid
from textual.binding import Binding
from textual.screen import Screen, ModalScreen
from textual.widgets import DataTable, Input

from .components import WorkflowTable, StatusDisplay, EnvironmentDisplay, GitStatusDisplay
from .custom_button import CustomButton


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
  
Git Commands:
  g          Show Git status
  c          Commit changes
  s          puSh to remote (git push)
  f          Fetch from remote (git pull)
  
Other:
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
    
    BINDINGS = [
        Binding("l", "list_workflows", "List", priority=True),
        Binding("u", "pull_workflow", "pUll", priority=True),
        Binding("p", "push_workflow", "Push", priority=True),
        Binding("e", "switch_env", "Env", priority=True),
        Binding("b", "switch_branch", "Branch", priority=True),
        Binding("r", "refresh", "Refresh", priority=True),
        Binding("g", "git_status", "Git status", priority=True),
        Binding("c", "git_commit", "Commit", priority=True),
        Binding("s", "git_push", "puSh git", priority=True),
        Binding("f", "git_pull", "Fetch git", priority=True),
        Binding("q", "quit", "Quit", priority=True),
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("ctrl+q", "quit", "Quit", show=False),
        Binding("?", "show_help", "Help", priority=True),
        Binding("f1", "show_help", "Help", show=False),
        Binding("/", "focus_search", "Search", show=False),
        Binding("escape", "app.pop_screen", "Back", show=False),
    ]
    
    def __init__(self, app_service, can_switch_environments: bool = True):
        super().__init__()
        self.app_service = app_service
        self.can_switch_environments = can_switch_environments
        
        # UI component wrappers
        self.workflow_table = None
        self.status_display = None
        self.environment_display = None
        self.git_status_display = None
        
        # Controller reference (will be set by main app)
        self.controller = None
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the screen."""
        yield Header()
        yield Container(
            Horizontal(
                Vertical(
                    Static("🔄 n8n Workflow Manager", id="title"),
                    Static(f"Environment: {self.app_service.state.current_environment}", id="env-status"),
                    Static(f"Branch: {self.app_service.state.current_branch}", id="branch-status"),
                    Static("", id="git-status"),
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
                CustomButton("List", id="btn-list", classes="primary"),
                CustomButton("Pull", id="btn-pull", classes="success"),
                CustomButton("Push", id="btn-push", classes="warning"),
                CustomButton("Switch Env", id="btn-env", disabled=not self.can_switch_environments),
                CustomButton("Switch Branch", id="btn-branch"),
                id="button-container"
            ),
            id="app-container"
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """Handle mount event."""
        # Initialize UI component wrappers
        table_widget = self.query_one("#workflow-table", DataTable)
        self.workflow_table = WorkflowTable(table_widget)
        self.workflow_table.setup()
        
        status_widget = self.query_one("#status-message", Static)
        self.status_display = StatusDisplay(status_widget)
        
        env_widget = self.query_one("#env-status", Static)
        branch_widget = self.query_one("#branch-status", Static)
        self.environment_display = EnvironmentDisplay(env_widget, branch_widget)
        
        git_widget = self.query_one("#git-status", Static)
        self.git_status_display = GitStatusDisplay(git_widget)
        
        # Update git status
        self.update_git_status()
        
        # Load initial data
        if self.app_service.api_client:
            self.action_list_workflows()
        else:
            # Load demo data
            demo_workflows = self.app_service.get_demo_workflows()
            self.app_service.state.workflows = demo_workflows
            self.app_service.state.filtered_workflows = demo_workflows
            self.workflow_table.update_workflows(demo_workflows)
            self.status_display.update_status("Loaded demo workflows")
        
        # Give focus to the table after loading data
        table_widget.focus()
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            search_term = event.value.lower()
            self.filter_workflows(search_term)
    
    def filter_workflows(self, search_term: str) -> None:
        """Filter workflows based on search term."""
        from domain.models import WorkflowFilter
        
        filter_criteria = WorkflowFilter(search_term=search_term)
        
        if self.app_service.workflow_service:
            filtered = self.app_service.workflow_service.filter_workflows(
                self.app_service.state.workflows,
                filter_criteria
            )
        else:
            # Demo mode filtering
            if not search_term:
                filtered = self.app_service.state.workflows
            else:
                filtered = [
                    w for w in self.app_service.state.workflows
                    if search_term in w.name.lower() or
                    search_term in w.id.lower() or
                    any(search_term in tag.lower() for tag in w.tags)
                ]
        
        self.app_service.state.filtered_workflows = filtered
        self.workflow_table.update_workflows(filtered)
    
    # Action methods with @work decorator for async operations
    @work(exclusive=True)
    async def action_list_workflows(self) -> None:
        """List workflows from n8n."""
        if self.controller:
            await self.controller.list_workflows()
    
    @work(exclusive=True)
    async def action_pull_workflow(self) -> None:
        """Pull selected workflow."""
        if self.controller:
            await self.controller.pull_workflow()
    
    @work(exclusive=True)
    async def action_push_workflow(self) -> None:
        """Push selected workflow."""
        if self.controller:
            await self.controller.push_workflow()
    
    async def action_switch_env(self) -> None:
        """Switch environment and branch."""
        if self.controller:
            await self.controller.switch_environment()
    
    def action_show_help(self) -> None:
        """Show help information."""
        self.app.push_screen(HelpScreen())
    
    def action_refresh(self) -> None:
        """Refresh the workflow list."""
        self.action_list_workflows()
    
    def action_focus_search(self) -> None:
        """Focus the search input box."""
        search_input = self.query_one("#search-input", Input)
        search_input.focus()
    
    def action_switch_branch(self) -> None:
        """Show branch information."""
        if self.controller:
            self.controller.show_branch_info()
    
    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses - implementation delegated to controller."""
        if self.controller:
            await self.controller.handle_button_press(event)
    
    async def on_custom_button_pressed(self, event: CustomButton.Pressed) -> None:
        """Handle custom button presses."""
        if self.controller:
            await self.controller.handle_button_press(event)
    
    def update_git_status(self):
        """Update the Git status display."""
        if self.git_status_display:
            status = self.app_service.get_git_status()
            self.git_status_display.update_status(status)
    
    def action_git_status(self) -> None:
        """Show Git status."""
        if self.controller:
            self.controller.show_git_status()
    
    @work(exclusive=True)
    async def action_git_commit(self) -> None:
        """Commit changes."""
        if self.controller:
            await self.controller.git_commit()
    
    @work(exclusive=True)
    async def action_git_push(self) -> None:
        """Push to remote."""
        if self.controller:
            await self.controller.git_push()
    
    @work(exclusive=True)
    async def action_git_pull(self) -> None:
        """Pull from remote."""
        if self.controller:
            await self.controller.git_pull()