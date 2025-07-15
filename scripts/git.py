import git
import logging
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class GitManager:
    """Manage Git operations for the workflow repository."""
    
    def __init__(self, repo_path: Path = Path.cwd()):
        """
        Initialize the Git manager.
        
        Args:
            repo_path: Path to the Git repository
        """
        self.repo_path = repo_path
        self._repo = None
    
    @property
    def repo(self) -> git.Repo:
        """Get or initialize the Git repository."""
        if self._repo is None:
            try:
                self._repo = git.Repo(self.repo_path)
            except git.InvalidGitRepositoryError:
                logger.info(f"Initializing new Git repository at {self.repo_path}")
                self._repo = git.Repo.init(self.repo_path)
        return self._repo
    
    def get_current_branch(self) -> str:
        """Get the name of the current branch."""
        try:
            return self.repo.active_branch.name
        except TypeError:
            return 'detached HEAD'
    
    def get_branches(self) -> List[str]:
        """Get list of all local branches."""
        return [branch.name for branch in self.repo.branches]
    
    def get_environment_branch(self, environment: str) -> str:
        """
        Get the branch name for a given environment.
        
        Args:
            environment: The environment name (dev, testing, staging, prod)
            
        Returns:
            The corresponding branch name
        """
        branch_mapping = {
            'dev': 'dev',
            'testing': 'testing',
            'staging': 'staging',
            'prod': 'main'
        }
        return branch_mapping.get(environment, 'main')
    
    def switch_to_environment_branch(self, environment: str) -> bool:
        """
        Switch to the appropriate branch for the given environment.
        Creates the branch if it doesn't exist.
        
        Args:
            environment: The environment name (dev, testing, staging, prod)
            
        Returns:
            True if successful
        """
        target_branch = self.get_environment_branch(environment)
        current_branch = self.get_current_branch()
        
        # Check if repository has any commits
        try:
            self.repo.head.commit
        except ValueError:
            logger.info(f"Repository has no commits yet, cannot switch branches")
            return False
        
        if current_branch == target_branch:
            logger.info(f"Already on branch {target_branch} for environment {environment}")
            return True
        
        logger.info(f"Switching from {current_branch} to {target_branch} for environment {environment}")
        return self.checkout_branch(target_branch, create=True)
    
    def checkout_branch(self, branch_name: str, create: bool = False) -> bool:
        """
        Checkout a branch.
        
        Args:
            branch_name: Name of the branch
            create: Create the branch if it doesn't exist
            
        Returns:
            True if successful
        """
        try:
            if create and branch_name not in self.get_branches():
                self.repo.create_head(branch_name)
                logger.info(f"Created new branch: {branch_name}")
            
            self.repo.heads[branch_name].checkout()
            logger.info(f"Checked out branch: {branch_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to checkout branch {branch_name}: {e}")
            return False
    
    def get_status(self) -> Tuple[List[str], List[str], List[str]]:
        """
        Get repository status.
        
        Returns:
            Tuple of (staged files, modified files, untracked files)
        """
        staged = [item.a_path for item in self.repo.index.diff('HEAD')]
        modified = [item.a_path for item in self.repo.index.diff(None)]
        untracked = self.repo.untracked_files
        
        return staged, modified, untracked
    
    def add_files(self, file_paths: List[str]) -> bool:
        """
        Add files to the staging area.
        
        Args:
            file_paths: List of file paths to add
            
        Returns:
            True if successful
        """
        try:
            self.repo.index.add(file_paths)
            logger.info(f"Added {len(file_paths)} files to staging area")
            return True
        except Exception as e:
            logger.error(f"Failed to add files: {e}")
            return False
    
    def commit(self, message: str, author: Optional[str] = None, 
               email: Optional[str] = None) -> Optional[str]:
        """
        Create a commit.
        
        Args:
            message: Commit message
            author: Author name (optional)
            email: Author email (optional)
            
        Returns:
            Commit SHA or None if failed
        """
        try:
            if author and email:
                actor = git.Actor(author, email)
                commit = self.repo.index.commit(message, author=actor, committer=actor)
            else:
                commit = self.repo.index.commit(message)
            
            logger.info(f"Created commit: {commit.hexsha[:8]}")
            return commit.hexsha
        except Exception as e:
            logger.error(f"Failed to create commit: {e}")
            return None
    
    def push(self, remote_name: str = 'origin', branch: Optional[str] = None) -> bool:
        """
        Push commits to remote.
        
        Args:
            remote_name: Name of the remote
            branch: Branch to push (uses current branch if None)
            
        Returns:
            True if successful
        """
        try:
            if branch is None:
                branch = self.get_current_branch()
            
            remote = self.repo.remote(remote_name)
            info = remote.push(branch)
            
            for push_info in info:
                if push_info.flags & push_info.ERROR:
                    logger.error(f"Push failed: {push_info.summary}")
                    return False
            
            logger.info(f"Successfully pushed to {remote_name}/{branch}")
            return True
        except Exception as e:
            logger.error(f"Failed to push: {e}")
            return False
    
    def pull(self, remote_name: str = 'origin', branch: Optional[str] = None) -> bool:
        """
        Pull changes from remote.
        
        Args:
            remote_name: Name of the remote
            branch: Branch to pull (uses current branch if None)
            
        Returns:
            True if successful
        """
        try:
            if branch is None:
                branch = self.get_current_branch()
            
            remote = self.repo.remote(remote_name)
            info = remote.pull(branch)
            
            for fetch_info in info:
                logger.info(f"Pulled {fetch_info.ref} from {remote_name}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to pull: {e}")
            return False
    
    def get_last_commit_info(self) -> Optional[Tuple[str, str, datetime]]:
        """
        Get information about the last commit.
        
        Returns:
            Tuple of (commit SHA, message, datetime) or None
        """
        try:
            commit = self.repo.head.commit
            return (
                commit.hexsha[:8],
                commit.message.strip(),
                datetime.fromtimestamp(commit.committed_date)
            )
        except Exception:
            return None
    
    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        return self.repo.is_dirty(untracked_files=True)
    
    def auto_commit_workflow_changes(self, workflow_id: str, workflow_name: str, 
                                   operation: str) -> Optional[str]:
        """
        Automatically commit workflow changes.
        
        Args:
            workflow_id: The workflow ID
            workflow_name: The workflow name
            operation: The operation performed (e.g., 'pulled', 'pushed')
            
        Returns:
            Commit SHA or None if no changes or failed
        """
        staged, modified, untracked = self.get_status()
        
        workflow_files = []
        for file_list in [staged, modified, untracked]:
            for file_path in file_list:
                if workflow_id in file_path:
                    workflow_files.append(file_path)
        
        if not workflow_files:
            logger.info("No workflow changes to commit")
            return None
        
        self.add_files(workflow_files)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"Workflow {operation}: {workflow_name} ({workflow_id}) - {timestamp}"
        
        return self.commit(message)
    
    def init_remote(self, remote_url: str, remote_name: str = 'origin') -> bool:
        """
        Initialize or update a remote.
        
        Args:
            remote_url: The remote repository URL
            remote_name: Name for the remote
            
        Returns:
            True if successful
        """
        try:
            try:
                remote = self.repo.remote(remote_name)
                remote.set_url(remote_url)
                logger.info(f"Updated remote {remote_name} URL to {remote_url}")
            except ValueError:
                self.repo.create_remote(remote_name, remote_url)
                logger.info(f"Added remote {remote_name} with URL {remote_url}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to init remote: {e}")
            return False