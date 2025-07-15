import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def sanitize_filename(name: str, max_length: int = 255) -> str:
    """
    Sanitize workflow name to create a valid filename.
    
    Args:
        name: Original workflow name
        max_length: Maximum filename length (default: 255)
        
    Returns:
        Sanitized filename without extension
    """
    sanitized = name.lower()
    sanitized = re.sub(r'\s+', '_', sanitized)
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', sanitized)
    sanitized = sanitized.strip('_-')
    
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    if not sanitized:
        sanitized = 'workflow'
    
    return sanitized


def create_metadata(workflow_id: str, original_name: str, environment: str) -> Dict[str, Any]:
    """
    Create metadata for a workflow.
    
    Args:
        workflow_id: The workflow ID from n8n
        original_name: The original workflow name
        environment: The environment (dev, staging, prod)
        
    Returns:
        Metadata dictionary
    """
    return {
        "original_name": original_name,
        "workflow_id": workflow_id,
        "last_pulled": datetime.utcnow().isoformat() + "Z",
        "environment": environment
    }


def generate_readme(workflow_data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
    """
    Generate README.md content for a workflow.
    
    Args:
        workflow_data: The workflow JSON data
        metadata: The workflow metadata
        
    Returns:
        README content as string
    """
    readme_content = f"# {metadata['original_name']}\n\n"
    readme_content += f"**Workflow ID:** {metadata['workflow_id']}  \n"
    readme_content += f"**Environment:** {metadata['environment']}  \n"
    readme_content += f"**Last Pulled:** {metadata['last_pulled']}  \n\n"
    
    if workflow_data.get('description'):
        readme_content += "## Description\n\n"
        readme_content += f"{workflow_data['description']}\n\n"
    
    if workflow_data.get('tags'):
        readme_content += "## Tags\n\n"
        for tag in workflow_data['tags']:
            readme_content += f"- {tag}\n"
        readme_content += "\n"
    
    if workflow_data.get('nodes'):
        readme_content += "## Nodes\n\n"
        readme_content += "This workflow contains the following nodes:\n\n"
        for node in workflow_data['nodes']:
            node_type = node.get('type', 'Unknown')
            node_name = node.get('name', 'Unnamed')
            readme_content += f"- **{node_name}** ({node_type})\n"
        readme_content += "\n"
    
    readme_content += "## Notes\n\n"
    readme_content += "_Add any additional notes or documentation here._\n"
    
    return readme_content


def save_workflow(workflow_data: Dict[str, Any], workflow_dir: Path, 
                  workflow_id: str, environment: str) -> Path:
    """
    Save a workflow to the filesystem with metadata and README.
    
    Args:
        workflow_data: The workflow JSON data
        workflow_dir: The base directory for workflows (e.g., workflows/devops)
        workflow_id: The workflow ID
        environment: The environment (dev, staging, prod)
        
    Returns:
        Path to the saved workflow directory
    """
    workflow_name = workflow_data.get('name', 'Unnamed Workflow')
    sanitized_name = sanitize_filename(workflow_name)
    
    workflow_path = workflow_dir / workflow_id
    workflow_path.mkdir(parents=True, exist_ok=True)
    
    workflow_file = workflow_path / f"{sanitized_name}.json"
    with open(workflow_file, 'w', encoding='utf-8') as f:
        json.dump(workflow_data, f, indent=2, ensure_ascii=False)
    
    metadata = create_metadata(workflow_id, workflow_name, environment)
    metadata_file = workflow_path / "metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    readme_content = generate_readme(workflow_data, metadata)
    readme_file = workflow_path / "README.md"
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    logger.info(f"Saved workflow {workflow_id} ({workflow_name}) to {workflow_path}")
    
    return workflow_path


def load_workflow_metadata(workflow_path: Path) -> Optional[Dict[str, Any]]:
    """
    Load metadata for a workflow from the filesystem.
    
    Args:
        workflow_path: Path to the workflow directory
        
    Returns:
        Metadata dictionary or None if not found
    """
    metadata_file = workflow_path / "metadata.json"
    if metadata_file.exists():
        with open(metadata_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def find_workflow_file(workflow_path: Path) -> Optional[Path]:
    """
    Find the workflow JSON file in a workflow directory.
    
    Args:
        workflow_path: Path to the workflow directory
        
    Returns:
        Path to the workflow JSON file or None if not found
    """
    json_files = list(workflow_path.glob("*.json"))
    for json_file in json_files:
        if json_file.name != "metadata.json":
            return json_file
    return None