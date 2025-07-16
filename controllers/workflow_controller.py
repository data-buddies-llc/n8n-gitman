"""
Controller for workflow operations and UI coordination.
"""
import asyncio
import logging
from datetime import datetime
from textual.widgets import Button

from domain.services import ApplicationService
from domain.models import WorkflowFilter
from ui.screens import WorkflowScreen

logger = logging.getLogger(__name__)


class WorkflowController:
    """Controller that coordinates between UI and business logic."""
    
    def __init__(self, screen: WorkflowScreen):
        self.screen = screen
        self.app_service: ApplicationService = screen.app_service
    
    async def list_workflows(self) -> None:
        """List workflows from n8n."""
        self.screen.status_display.update_status("Fetching workflows...")
        
        try:
            result = await asyncio.to_thread(self.app_service.workflow_service.list_workflows)
            
            if result.success:
                self.app_service.state.workflows = result.data
                self.app_service.state.filtered_workflows = result.data
                self.screen.workflow_table.update_workflows(result.data)
                self.screen.status_display.update_status(result.message)
                self.app_service.state.last_operation = f"Listed at {datetime.now().strftime('%H:%M:%S')}"
            else:
                self.screen.status_display.update_status(result.message, is_error=True)
                
        except Exception as e:
            logger.error(f"Error in list_workflows: {e}")
            self.screen.status_display.update_status(f"Error: {str(e)}", is_error=True)
    
    async def pull_workflow(self) -> None:
        """Pull selected workflow."""
        selected_workflow = self.screen.workflow_table.get_selected_workflow()
        
        if not selected_workflow:
            self.screen.status_display.update_status("No workflow selected", is_error=True)
            return
        
        self.screen.status_display.update_status(f"Pulling workflow: {selected_workflow.name}...")
        
        try:
            result = await asyncio.to_thread(
                self.app_service.workflow_service.pull_workflow,
                selected_workflow,
                self.app_service.state.current_environment
            )
            
            if result.success:
                self.screen.status_display.update_status(result.message)
                self.app_service.state.last_operation = f"Pulled at {datetime.now().strftime('%H:%M:%S')}"
                # Refresh the workflow list to update "In Repo" status
                await self.list_workflows()
            else:
                self.screen.status_display.update_status(result.message, is_error=True)
                
        except Exception as e:
            logger.error(f"Error in pull_workflow: {e}")
            self.screen.status_display.update_status(f"Error pulling workflow: {str(e)}", is_error=True)
    
    async def push_workflow(self) -> None:
        """Push selected workflow."""
        selected_workflow = self.screen.workflow_table.get_selected_workflow()
        
        if not selected_workflow:
            self.screen.status_display.update_status("No workflow selected", is_error=True)
            return
        
        self.screen.status_display.update_status(f"Pushing workflow: {selected_workflow.name}...")
        
        try:
            result = await asyncio.to_thread(
                self.app_service.workflow_service.push_workflow,
                selected_workflow
            )
            
            if result.success:
                self.screen.status_display.update_status(result.message)
                self.app_service.state.last_operation = f"Pushed at {datetime.now().strftime('%H:%M:%S')}"
            else:
                self.screen.status_display.update_status(result.message, is_error=True)
                
        except Exception as e:
            logger.error(f"Error in push_workflow: {e}")
            self.screen.status_display.update_status(f"Error pushing workflow: {str(e)}", is_error=True)
    
    async def switch_environment(self) -> None:
        """Switch environment and corresponding git branch."""
        if not self.screen.can_switch_environments:
            self.screen.status_display.update_status(
                "Environment switching disabled - only one environment configured", 
                is_error=True
            )
            return
        
        available_environments = self.app_service.environment_service.get_available_environments()
        env_names = [env.name for env in available_environments]
        
        try:
            current_idx = env_names.index(self.app_service.state.current_environment)
            next_idx = (current_idx + 1) % len(env_names)
            new_environment = env_names[next_idx]
            
            # Switch environment
            result = self.app_service.environment_service.switch_environment(new_environment)
            
            if result.success:
                # Update application state
                self.app_service.state.current_environment = new_environment
                self.app_service.state.current_branch = result.data["branch"]
                
                # Reinitialize API client
                from scripts.api import N8NAPIClient
                if self.app_service.api_client:
                    self.app_service.api_client.close()
                self.app_service.api_client = N8NAPIClient(new_environment)
                
                from domain.services import WorkflowService
                self.app_service.workflow_service = WorkflowService(
                    self.app_service.api_client, 
                    self.app_service.git_manager
                )
                
                # Update UI
                self.screen.environment_display.update_both(new_environment, result.data["branch"])
                self.screen.status_display.update_status(result.message)
                
                # Refresh workflows for new environment
                await self.list_workflows()
            else:
                self.screen.status_display.update_status(result.message, is_error=True)
                
        except Exception as e:
            logger.error(f"Error switching environment: {e}")
            self.screen.status_display.update_status(f"Error switching environment: {str(e)}", is_error=True)
    
    def show_branch_info(self) -> None:
        """Show branch information."""
        branch_info = self.app_service.get_branch_info()
        self.screen.status_display.update_status(branch_info)
    
    async def handle_button_press(self, event) -> None:
        """Handle button press events."""
        button_id = event.button.id
        
        if button_id == "btn-list":
            if self.app_service.api_client:
                await self.list_workflows()
            else:
                # Demo mode
                demo_workflows = self.app_service.get_demo_workflows()
                self.app_service.state.workflows = demo_workflows
                self.app_service.state.filtered_workflows = demo_workflows
                self.screen.workflow_table.update_workflows(demo_workflows)
                self.screen.status_display.update_status("Loaded demo workflows")
                
        elif button_id == "btn-pull":
            if self.app_service.api_client:
                await self.pull_workflow()
            else:
                self.screen.status_display.update_status("Pull disabled in demo mode", is_error=True)
                
        elif button_id == "btn-push":
            if self.app_service.api_client:
                await self.push_workflow()
            else:
                self.screen.status_display.update_status("Push disabled in demo mode", is_error=True)
                
        elif button_id == "btn-env":
            if self.screen.can_switch_environments:
                await self.switch_environment()
            else:
                self.screen.status_display.update_status(
                    "Environment switching disabled - only one environment configured", 
                    is_error=True
                )
                
        elif button_id == "btn-branch":
            self.show_branch_info()
    
    def show_git_status(self) -> None:
        """Show detailed Git status."""
        status = self.app_service.get_git_status()
        
        status_parts = []
        if status['has_remote']:
            if status['is_synced']:
                status_parts.append("✓ Repository is synced")
            else:
                if status['is_ahead']:
                    status_parts.append(f"↑ {status['ahead_count']} commits ahead")
                if status['is_behind']:
                    status_parts.append(f"↓ {status['behind_count']} commits behind")
        else:
            status_parts.append("No remote repository configured")
        
        if status['has_uncommitted']:
            uncommitted = []
            if status['staged_count']:
                uncommitted.append(f"{status['staged_count']} staged")
            if status['modified_count']:
                uncommitted.append(f"{status['modified_count']} modified")
            if status['untracked_count']:
                uncommitted.append(f"{status['untracked_count']} untracked")
            status_parts.append(f"Local changes: {', '.join(uncommitted)}")
        
        message = " | ".join(status_parts) if status_parts else "No Git status available"
        self.screen.status_display.update_status(message)
    
    async def git_commit(self) -> None:
        """Commit all changes."""
        self.screen.status_display.update_status("Committing changes...")
        
        try:
            # Get current status
            status = self.app_service.get_git_status()
            
            if not status['has_uncommitted']:
                self.screen.status_display.update_status("No changes to commit")
                return
            
            # Add all files
            git_manager = self.app_service.git_manager
            staged, modified, untracked = git_manager.get_status()
            
            all_files = list(set(staged + modified + untracked))
            if all_files:
                success = await asyncio.to_thread(git_manager.add_files, all_files)
                if not success:
                    self.screen.status_display.update_status("Failed to add files", is_error=True)
                    return
            
            # Create commit
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_message = f"Automated commit - {timestamp}"
            
            commit_sha = await asyncio.to_thread(git_manager.commit, commit_message)
            
            if commit_sha:
                self.screen.status_display.update_status(f"Committed changes: {commit_sha[:8]}")
                # Update git status display
                self.screen.update_git_status()
            else:
                self.screen.status_display.update_status("Failed to create commit", is_error=True)
                
        except Exception as e:
            logger.error(f"Error in git_commit: {e}")
            self.screen.status_display.update_status(f"Error committing: {str(e)}", is_error=True)
    
    async def git_push(self) -> None:
        """Push to remote repository."""
        self.screen.status_display.update_status("Pushing to remote...")
        
        try:
            git_manager = self.app_service.git_manager
            success = await asyncio.to_thread(git_manager.push)
            
            if success:
                self.screen.status_display.update_status("Successfully pushed to remote")
                # Update git status display
                self.screen.update_git_status()
            else:
                self.screen.status_display.update_status("Failed to push to remote", is_error=True)
                
        except Exception as e:
            logger.error(f"Error in git_push: {e}")
            self.screen.status_display.update_status(f"Error pushing: {str(e)}", is_error=True)
    
    async def git_pull(self) -> None:
        """Pull from remote repository."""
        self.screen.status_display.update_status("Pulling from remote...")
        
        try:
            git_manager = self.app_service.git_manager
            success = await asyncio.to_thread(git_manager.pull)
            
            if success:
                self.screen.status_display.update_status("Successfully pulled from remote")
                # Update git status display
                self.screen.update_git_status()
                # Refresh workflows as they might have changed
                if self.app_service.api_client:
                    await self.list_workflows()
            else:
                self.screen.status_display.update_status("Failed to pull from remote", is_error=True)
                
        except Exception as e:
            logger.error(f"Error in git_pull: {e}")
            self.screen.status_display.update_status(f"Error pulling: {str(e)}", is_error=True)