import httpx
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class N8NAPIClient:
    """Client for interacting with n8n API."""
    
    @staticmethod
    def get_available_environments() -> List[str]:
        """Get list of available environments based on configuration."""
        load_dotenv()
        available = []
        
        for env in ['dev', 'staging', 'prod']:
            url_key = f"N8N_{env.upper()}_URL"
            api_key_key = f"N8N_{env.upper()}_API_KEY"
            
            if os.getenv(url_key) and os.getenv(api_key_key):
                available.append(env)
        
        return available
    
    def __init__(self, environment: str = None):
        """
        Initialize the n8n API client.
        
        Args:
            environment: The environment to use (dev, staging, prod)
        """
        load_dotenv()
        
        if environment is None:
            environment = os.getenv('DEFAULT_N8N_ENV', 'dev').lower()
        
        self.environment = environment
        self.base_url = self._get_base_url(environment)
        self.api_key = self._get_api_key(environment)
        
        if not self.base_url or not self.api_key:
            raise ValueError(f"Missing API configuration for environment: {environment}")
        
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={
                "X-N8N-API-KEY": self.api_key,
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
        
        self.retry_config = {
            'max_attempts': 3,
            'backoff_factor': 2.0
        }
    
    def _get_base_url(self, environment: str) -> Optional[str]:
        """Get the base URL for the specified environment."""
        env_key = f"N8N_{environment.upper()}_URL"
        url = os.getenv(env_key)
        if url and not url.endswith('/'):
            url += '/'
        return url
    
    def _get_api_key(self, environment: str) -> Optional[str]:
        """Get the API key for the specified environment."""
        env_key = f"N8N_{environment.upper()}_API_KEY"
        return os.getenv(env_key)
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Make a request with retry logic."""
        attempts = 0
        last_error = None
        
        while attempts < self.retry_config['max_attempts']:
            try:
                response = self.client.request(method, endpoint, **kwargs)
                response.raise_for_status()
                return response
            except httpx.HTTPError as e:
                last_error = e
                attempts += 1
                if attempts < self.retry_config['max_attempts']:
                    wait_time = self.retry_config['backoff_factor'] ** attempts
                    logger.warning(f"Request failed, retrying in {wait_time}s... (attempt {attempts})")
                    import time
                    time.sleep(wait_time)
        
        raise last_error
    
    def list_workflows(self, active: Optional[bool] = None, tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        List all workflows.
        
        Args:
            active: Filter by active status
            tags: Filter by tags
            
        Returns:
            List of workflow summaries
        """
        params = {}
        if active is not None:
            params['active'] = str(active).lower()
        if tags:
            params['tags'] = ','.join(tags)
        
        try:
            response = self._make_request('GET', 'api/v1/workflows', params=params)
            data = response.json()
            return data.get('data', [])
        except Exception as e:
            logger.error(f"Failed to list workflows: {e}")
            raise
    
    def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get a specific workflow by ID.
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            Workflow data
        """
        try:
            response = self._make_request('GET', f'api/v1/workflows/{workflow_id}')
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get workflow {workflow_id}: {e}")
            raise
    
    def create_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new workflow.
        
        Args:
            workflow_data: The workflow data
            
        Returns:
            Created workflow data with ID
        """
        workflow_data.pop('id', None)
        
        try:
            response = self._make_request('POST', 'api/v1/workflows', json=workflow_data)
            data = response.json()
            return data.get('data', {})
        except Exception as e:
            logger.error(f"Failed to create workflow: {e}")
            raise
    
    def update_workflow(self, workflow_id: str, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing workflow.
        
        Args:
            workflow_id: The workflow ID
            workflow_data: The updated workflow data
            
        Returns:
            Updated workflow data
        """
        workflow_data.pop('id', None)
        
        try:
            response = self._make_request('PUT', f'api/v1/workflows/{workflow_id}', json=workflow_data)
            data = response.json()
            return data.get('data', {})
        except Exception as e:
            logger.error(f"Failed to update workflow {workflow_id}: {e}")
            raise
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """
        Delete a workflow.
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            True if successful
        """
        try:
            self._make_request('DELETE', f'api/v1/workflows/{workflow_id}')
            return True
        except Exception as e:
            logger.error(f"Failed to delete workflow {workflow_id}: {e}")
            return False
    
    def activate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Activate a workflow.
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            Updated workflow data
        """
        try:
            response = self._make_request('PATCH', f'api/v1/workflows/{workflow_id}/activate')
            data = response.json()
            return data.get('data', {})
        except Exception as e:
            logger.error(f"Failed to activate workflow {workflow_id}: {e}")
            raise
    
    def deactivate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Deactivate a workflow.
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            Updated workflow data
        """
        try:
            response = self._make_request('PATCH', f'api/v1/workflows/{workflow_id}/deactivate')
            data = response.json()
            return data.get('data', {})
        except Exception as e:
            logger.error(f"Failed to deactivate workflow {workflow_id}: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Test the API connection.
        
        Returns:
            True if connection is successful
        """
        try:
            self._make_request('GET', 'api/v1/workflows?limit=1')
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()