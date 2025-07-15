import pytest
from unittest.mock import Mock, patch, MagicMock
import httpx
from scripts.api import N8NAPIClient


class TestN8NAPIClient:
    @patch.dict('os.environ', {
        'N8N_DEV_URL': 'https://dev.example.com',
        'N8N_DEV_API_KEY': 'dev-key',
        'N8N_STAGING_URL': 'https://staging.example.com',
        'N8N_STAGING_API_KEY': 'staging-key',
        'N8N_PROD_URL': 'https://prod.example.com',
        'N8N_PROD_API_KEY': 'prod-key'
    })
    def test_initialization(self):
        client = N8NAPIClient('dev')
        assert client.environment == 'dev'
        assert client.base_url == 'https://dev.example.com/'
        assert client.api_key == 'dev-key'
        
        client = N8NAPIClient('staging')
        assert client.environment == 'staging'
        assert client.base_url == 'https://staging.example.com/'
        
    @patch('scripts.api.load_dotenv')
    @patch.dict('os.environ', {}, clear=True)
    def test_missing_config(self, mock_load_dotenv):
        with pytest.raises(ValueError):
            N8NAPIClient('dev')
    
    @patch('scripts.api.load_dotenv')
    @patch.dict('os.environ', {
        'N8N_DEV_URL': 'https://dev.example.com',
        'N8N_DEV_API_KEY': 'dev-key',
        'N8N_PROD_URL': 'https://prod.example.com',
        'N8N_PROD_API_KEY': 'prod-key'
    }, clear=True)
    def test_get_available_environments(self, mock_load_dotenv):
        environments = N8NAPIClient.get_available_environments()
        assert 'dev' in environments
        assert 'prod' in environments
        assert 'staging' not in environments
        assert len(environments) == 2
    
    @patch('scripts.api.load_dotenv')
    @patch.dict('os.environ', {}, clear=True)
    def test_get_available_environments_empty(self, mock_load_dotenv):
        environments = N8NAPIClient.get_available_environments()
        assert environments == []
    
    @patch.dict('os.environ', {
        'N8N_DEV_URL': 'https://dev.example.com',
        'N8N_DEV_API_KEY': 'dev-key'
    })
    def test_list_workflows(self):
        client = N8NAPIClient('dev')
        
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': [
                {'id': '1', 'name': 'Workflow 1'},
                {'id': '2', 'name': 'Workflow 2'}
            ]
        }
        
        with patch.object(client, '_make_request', return_value=mock_response):
            workflows = client.list_workflows()
            
            assert len(workflows) == 2
            assert workflows[0]['id'] == '1'
            assert workflows[1]['name'] == 'Workflow 2'
    
    @patch.dict('os.environ', {
        'N8N_DEV_URL': 'https://dev.example.com',
        'N8N_DEV_API_KEY': 'dev-key'
    })
    def test_get_workflow(self):
        client = N8NAPIClient('dev')
        
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': {
                'id': '123',
                'name': 'Test Workflow',
                'nodes': []
            }
        }
        
        with patch.object(client, '_make_request', return_value=mock_response):
            workflow = client.get_workflow('123')
            
            assert workflow['id'] == '123'
            assert workflow['name'] == 'Test Workflow'
    
    @patch.dict('os.environ', {
        'N8N_DEV_URL': 'https://dev.example.com',
        'N8N_DEV_API_KEY': 'dev-key'
    })
    def test_create_workflow(self):
        client = N8NAPIClient('dev')
        
        workflow_data = {
            'name': 'New Workflow',
            'nodes': []
        }
        
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': {
                'id': '456',
                'name': 'New Workflow',
                'nodes': []
            }
        }
        
        with patch.object(client, '_make_request', return_value=mock_response):
            created = client.create_workflow(workflow_data)
            
            assert created['id'] == '456'
            assert created['name'] == 'New Workflow'
    
    @patch.dict('os.environ', {
        'N8N_DEV_URL': 'https://dev.example.com',
        'N8N_DEV_API_KEY': 'dev-key'
    })
    def test_update_workflow(self):
        client = N8NAPIClient('dev')
        
        workflow_data = {
            'name': 'Updated Workflow',
            'nodes': []
        }
        
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': {
                'id': '123',
                'name': 'Updated Workflow',
                'nodes': []
            }
        }
        
        with patch.object(client, '_make_request', return_value=mock_response):
            updated = client.update_workflow('123', workflow_data)
            
            assert updated['id'] == '123'
            assert updated['name'] == 'Updated Workflow'
    
    @patch.dict('os.environ', {
        'N8N_DEV_URL': 'https://dev.example.com',
        'N8N_DEV_API_KEY': 'dev-key'
    })
    def test_delete_workflow(self):
        client = N8NAPIClient('dev')
        
        mock_response = Mock()
        
        with patch.object(client, '_make_request', return_value=mock_response):
            result = client.delete_workflow('123')
            assert result is True
    
    @patch.dict('os.environ', {
        'N8N_DEV_URL': 'https://dev.example.com',
        'N8N_DEV_API_KEY': 'dev-key'
    })
    def test_test_connection(self):
        client = N8NAPIClient('dev')
        
        mock_response = Mock()
        
        with patch.object(client, '_make_request', return_value=mock_response):
            result = client.test_connection()
            assert result is True
        
        with patch.object(client, '_make_request', side_effect=Exception("Connection failed")):
            result = client.test_connection()
            assert result is False
    
    @patch.dict('os.environ', {
        'N8N_DEV_URL': 'https://dev.example.com',
        'N8N_DEV_API_KEY': 'dev-key'
    })
    def test_retry_logic(self):
        client = N8NAPIClient('dev')
        
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.json.return_value = {'data': []}
        
        mock_client.request.side_effect = [
            httpx.HTTPError("Network error"),
            httpx.HTTPError("Network error"),
            mock_response
        ]
        
        client.client = mock_client
        
        with patch('time.sleep'):
            response = client._make_request('GET', 'test')
            assert response == mock_response
            assert mock_client.request.call_count == 3