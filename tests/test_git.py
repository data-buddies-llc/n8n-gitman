import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import git
from scripts.git import GitManager


class TestGitManager:
    def test_initialization(self, tmp_path):
        manager = GitManager(tmp_path)
        assert manager.repo_path == tmp_path
        assert manager._repo is None
    
    @patch('git.Repo')
    def test_repo_property_existing(self, mock_repo_class, tmp_path):
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        manager = GitManager(tmp_path)
        repo = manager.repo
        
        assert repo == mock_repo
        mock_repo_class.assert_called_once_with(tmp_path)
    
    @patch('git.Repo')
    @patch('git.Repo.init')
    def test_repo_property_new(self, mock_init, mock_repo_class, tmp_path):
        mock_repo_class.side_effect = git.InvalidGitRepositoryError
        mock_new_repo = Mock()
        mock_init.return_value = mock_new_repo
        
        manager = GitManager(tmp_path)
        repo = manager.repo
        
        assert repo == mock_new_repo
        mock_init.assert_called_once_with(tmp_path)
    
    def test_get_current_branch(self, tmp_path):
        manager = GitManager(tmp_path)
        
        mock_repo = Mock()
        mock_branch = Mock()
        mock_branch.name = "main"
        mock_repo.active_branch = mock_branch
        manager._repo = mock_repo
        
        assert manager.get_current_branch() == "main"
    
    def test_get_current_branch_detached(self, tmp_path):
        manager = GitManager(tmp_path)
        
        mock_repo = Mock()
        mock_repo.active_branch.side_effect = TypeError
        manager._repo = mock_repo
        
        assert manager.get_current_branch() == "detached HEAD"
    
    def test_get_branches(self, tmp_path):
        manager = GitManager(tmp_path)
        
        mock_repo = Mock()
        mock_branch1 = Mock()
        mock_branch1.name = "main"
        mock_branch2 = Mock()
        mock_branch2.name = "develop"
        mock_repo.branches = [mock_branch1, mock_branch2]
        manager._repo = mock_repo
        
        branches = manager.get_branches()
        assert branches == ["main", "develop"]
    
    def test_checkout_branch_existing(self, tmp_path):
        manager = GitManager(tmp_path)
        
        mock_repo = Mock()
        mock_branch = Mock()
        mock_repo.heads = {"main": mock_branch}
        manager._repo = mock_repo
        
        with patch.object(manager, 'get_branches', return_value=["main"]):
            result = manager.checkout_branch("main")
            
            assert result is True
            mock_branch.checkout.assert_called_once()
    
    def test_checkout_branch_create_new(self, tmp_path):
        manager = GitManager(tmp_path)
        
        mock_repo = Mock()
        mock_new_branch = Mock()
        mock_repo.create_head.return_value = mock_new_branch
        mock_repo.heads = {"new-branch": mock_new_branch}
        manager._repo = mock_repo
        
        with patch.object(manager, 'get_branches', return_value=[]):
            result = manager.checkout_branch("new-branch", create=True)
            
            assert result is True
            mock_repo.create_head.assert_called_once_with("new-branch")
            mock_new_branch.checkout.assert_called_once()
    
    def test_get_status(self, tmp_path):
        manager = GitManager(tmp_path)
        
        mock_repo = Mock()
        mock_staged = Mock()
        mock_staged.a_path = "staged.txt"
        mock_modified = Mock()
        mock_modified.a_path = "modified.txt"
        
        mock_repo.index.diff.side_effect = lambda x: {
            'HEAD': [mock_staged],
            None: [mock_modified]
        }.get(x, [])
        
        mock_repo.untracked_files = ["untracked.txt"]
        manager._repo = mock_repo
        
        staged, modified, untracked = manager.get_status()
        
        assert staged == ["staged.txt"]
        assert modified == ["modified.txt"]
        assert untracked == ["untracked.txt"]
    
    def test_add_files(self, tmp_path):
        manager = GitManager(tmp_path)
        
        mock_repo = Mock()
        manager._repo = mock_repo
        
        result = manager.add_files(["file1.txt", "file2.txt"])
        
        assert result is True
        mock_repo.index.add.assert_called_once_with(["file1.txt", "file2.txt"])
    
    def test_commit(self, tmp_path):
        manager = GitManager(tmp_path)
        
        mock_repo = Mock()
        mock_commit = Mock()
        mock_commit.hexsha = "abcdef1234567890"
        mock_repo.index.commit.return_value = mock_commit
        manager._repo = mock_repo
        
        sha = manager.commit("Test commit")
        
        assert sha == "abcdef1234567890"
        mock_repo.index.commit.assert_called_once_with("Test commit")
    
    def test_commit_with_author(self, tmp_path):
        manager = GitManager(tmp_path)
        
        mock_repo = Mock()
        mock_commit = Mock()
        mock_commit.hexsha = "abcdef1234567890"
        mock_repo.index.commit.return_value = mock_commit
        manager._repo = mock_repo
        
        with patch('git.Actor') as mock_actor:
            mock_actor_instance = Mock()
            mock_actor.return_value = mock_actor_instance
            
            sha = manager.commit("Test commit", author="Test User", email="test@example.com")
            
            assert sha == "abcdef1234567890"
            mock_actor.assert_called_once_with("Test User", "test@example.com")
            mock_repo.index.commit.assert_called_once_with(
                "Test commit",
                author=mock_actor_instance,
                committer=mock_actor_instance
            )
    
    def test_has_uncommitted_changes(self, tmp_path):
        manager = GitManager(tmp_path)
        
        mock_repo = Mock()
        mock_repo.is_dirty.return_value = True
        manager._repo = mock_repo
        
        assert manager.has_uncommitted_changes() is True
        mock_repo.is_dirty.assert_called_once_with(untracked_files=True)
    
    def test_auto_commit_workflow_changes(self, tmp_path):
        manager = GitManager(tmp_path)
        
        with patch.object(manager, 'get_status', return_value=(
            ["workflows/123/workflow.json"],
            ["workflows/123/metadata.json"],
            ["workflows/123/README.md"]
        )):
            with patch.object(manager, 'add_files') as mock_add:
                with patch.object(manager, 'commit', return_value="abc123") as mock_commit:
                    sha = manager.auto_commit_workflow_changes("123", "Test Workflow", "pulled")
                    
                    assert sha == "abc123"
                    mock_add.assert_called_once()
                    files_added = mock_add.call_args[0][0]
                    assert len(files_added) == 3
                    assert all("123" in f for f in files_added)
    
    def test_auto_commit_no_changes(self, tmp_path):
        manager = GitManager(tmp_path)
        
        with patch.object(manager, 'get_status', return_value=([], [], [])):
            sha = manager.auto_commit_workflow_changes("123", "Test Workflow", "pulled")
            assert sha is None