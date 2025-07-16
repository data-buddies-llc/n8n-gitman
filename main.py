#!/usr/bin/env python3
"""
Main entry point for the n8n Workflow Manager.
"""
import os
import sys
import yaml
import logging
from pathlib import Path

from textual.app import App
from textual.binding import Binding

from domain.services import ApplicationService
from ui.screens import WorkflowScreen, HelpScreen
from controllers.workflow_controller import WorkflowController

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class N8NWorkflowManager(App):
    """n8n Workflow Manager TUI Application."""
    
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("ctrl+q", "quit", "Quit", show=False),
    ]
    
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
        min-width: 16;
        padding: 0 2;
        height: 3;
        content-align: center middle;
        text-align: center;
    }
    
    /* Custom Button Styles */
    CustomButton {
        margin: 0 1;
        min-width: 16;
        padding: 0 2;
        height: 3;
        content-align: center middle;
        text-align: center;
        border: solid $accent;
        background: $surface;
        color: $text;
    }
    
    CustomButton:focus {
        text-style: bold;
        border: solid $primary;
        background: $primary-lighten-1;
    }
    
    CustomButton:hover {
        background: $primary-darken-1;
    }
    
    CustomButton.primary {
        background: $primary;
        color: $text;
        border: solid $primary;
    }
    
    CustomButton.success {
        background: $success;
        color: $text;
        border: solid $success;
    }
    
    CustomButton.warning {
        background: $warning;
        color: $text;
        border: solid $warning;
    }
    
    CustomButton.disabled {
        background: $surface-lighten-1;
        color: $text-muted;
        border: solid $surface-lighten-1;
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
        self.app_service = ApplicationService()
        self.workflow_controller = None
    
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
        # Initialize the application service
        environment = os.getenv('DEFAULT_N8N_ENV', 'dev')
        init_result = self.app_service.initialize(environment)
        
        if not init_result.success:
            logger.error(f"Failed to initialize application: {init_result.message}")
        
        # Create and push the main workflow screen
        can_switch_environments = self.app_service.can_switch_environments()
        workflow_screen = WorkflowScreen(self.app_service, can_switch_environments)
        
        # Create controller and connect it to the screen
        self.workflow_controller = WorkflowController(workflow_screen)
        self._connect_controller_to_screen(workflow_screen)
        
        self.push_screen(workflow_screen)
    
    def _connect_controller_to_screen(self, screen: WorkflowScreen):
        """Connect the controller to the screen."""
        # Set the controller reference on the screen
        screen.controller = self.workflow_controller


def main():
    """Main entry point."""
    app = N8NWorkflowManager()
    app.run()


if __name__ == "__main__":
    main()