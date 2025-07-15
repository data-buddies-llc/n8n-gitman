# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

n8n Workflow Git Manager - A Python terminal UI application for managing n8n workflows across multiple environments (Dev, Staging, Production) with Git integration. Built with the Textual framework for a modern TUI experience.

## Architecture

The application follows a modular architecture:

- **main.py**: Entry point containing the Textual UI application and event handlers
- **scripts/api.py**: n8n API client with retry logic and environment-specific endpoints
- **scripts/git.py**: Git operations manager handling commits, branches, and repository state
- **scripts/utils.py**: Utilities for file handling, path sanitization, and README generation

Key patterns:
- Environment-based configuration with `.env` files for API credentials
- Repository-based workflow storage with metadata tracking
- Automatic Git commits for workflow changes (configurable)
- Structured workflow directories: `workflows/{category}/{workflow_id}/`

## Common Commands

### Setup
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with actual n8n API credentials
```

### Run Application
```bash
python main.py
```

### Run Tests
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_api.py

# Run with coverage
pytest --cov=scripts tests/

# Run single test
pytest tests/test_api.py::test_function_name
```

### Development Tasks
- No linting configuration found - consider adding when requested
- No type checking configuration - consider adding mypy when requested
- Direct Python execution - no build process required

## Key Implementation Details

1. **Multi-Environment Support**: The app maintains up to three n8n connections (dev/staging/prod) configured via environment variables. Environment switching is automatically disabled if only one environment is configured. The app detects available environments using `N8NAPIClient.get_available_environments()`.

2. **Workflow Storage Structure**: Each workflow is stored in `workflows/{category}/{workflow_id}/` with three files:
   - `{sanitized_name}.json`: The actual workflow definition
   - `metadata.json`: Workflow metadata (name, tags, dates, etc.)
   - `README.md`: Auto-generated documentation

3. **API Integration**: The n8n API client in `scripts/api.py` handles:
   - Environment detection and availability checking
   - Workflow listing with pagination support
   - Workflow retrieval and updates
   - Retry logic with exponential backoff
   - Environment-specific authentication

4. **Git Integration**: Automatic Git operations can be enabled/disabled via `config.yaml`. The git module handles branch detection, commit creation, and repository state management.

5. **UI State Management**: The Textual app maintains workflow lists, current environment, and UI state. Uses single-letter key bindings (l, u, p, e, b, r, q, ?) for better terminal compatibility. Environment switching (e) shows an error message when only one environment is configured. The "Switch Env" button is disabled when only one environment is configured.

## Testing Approach

The project uses pytest with test files mirroring the module structure. Tests focus on:
- API client behavior with mocked responses
- Git operations with temporary repositories
- Utility functions for path handling and file operations

When adding new features, create corresponding test files following the existing pattern.