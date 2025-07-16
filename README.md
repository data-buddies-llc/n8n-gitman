# n8n Workflow Git Manager

A Python utility with a Textual-based UI for managing n8n workflows in Git repositories. This tool supports multiple n8n instances (Dev, Staging, Prod) and provides a unified interface for pulling, pushing, and managing workflows.

## Features

- **Multi-environment Support**: Manage workflows across Dev, Staging, and Production n8n instances
- **Git Integration**: Full Git support with status tracking, commit, push, and pull operations
- **GitHub Sync**: Real-time sync status showing ahead/behind commits and uncommitted changes
- **Textual UI**: Modern terminal user interface with keyboard shortcuts
- **Workflow Management**: Pull, push, list, and manage workflows
- **Search & Filter**: Find workflows by name, ID, or tags
- **Metadata Tracking**: Store workflow metadata and generate README files
- **Backup System**: Automatic backups before overwriting workflows

## Directory Structure

```
.
├── .env                    # Environment variables (create from .env.example)
├── .gitignore             # Git ignore file
├── README.md              # This file
├── requirements.txt       # Python dependencies
├── config.yaml           # Configuration settings
├── main.py               # Main application entry point
├── scripts/              # Core modules
│   ├── __init__.py
│   ├── api.py            # n8n API interactions
│   ├── git.py            # Git operations
│   └── utils.py          # Utility functions
├── workflows/            # Workflow storage
│   ├── biz/             # Business workflows
│   └── devops/          # DevOps workflows
├── tests/               # Test files
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_git.py
│   └── test_utils.py
└── docs/                # Documentation
    ├── setup.md
    └── usage.md
```

## Installation

1. **Clone or download** this repository
2. **Install Python 3.10+** if not already installed
3. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. **Copy the example environment file**:
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env`** with your n8n instance details:
   ```bash
   N8N_DEV_URL=https://your-dev-n8n.example.com
   N8N_DEV_API_KEY=your-dev-api-key
   N8N_STAGING_URL=https://your-staging-n8n.example.com
   N8N_STAGING_API_KEY=your-staging-api-key
   N8N_PROD_URL=https://your-prod-n8n.example.com
   N8N_PROD_API_KEY=your-prod-api-key
   DEFAULT_N8N_ENV=dev
   DEFAULT_WORKFLOW_DIR=workflows/devops
   LOG_LEVEL=INFO
   ```

3. **Obtain n8n API Keys**:
   - Go to your n8n instance
   - Navigate to Settings → API
   - Generate an API key for each environment

## Usage

### Starting the Application

```bash
python main.py
```

### Keyboard Shortcuts

#### Workflow Operations
| Shortcut | Action |
|----------|--------|
| `l` | List workflows from current environment |
| `u` | Pull selected workflow |
| `p` | Push selected workflow |
| `e` | Switch environment (Dev → Staging → Prod) |
| `b` | Show branch information |
| `r` | Refresh workflow list |
| `/` | Focus search box |
| `?` | Show help |
| `q` | Quit application |

#### Git Operations
| Shortcut | Action |
|----------|--------|
| `g` | Show Git status |
| `c` | Commit all changes |
| `s` | Push to remote (git push) |
| `f` | Fetch/pull from remote (git pull) |

### Workflow Operations

#### List Workflows
- Press `l` or click "List" button
- Shows all workflows from the current n8n environment
- Displays ID, Name, Repository status, Active status, Tags, and Last Modified

#### Pull Workflow
- Select a workflow from the list
- Press `u` or click "Pull" button
- Downloads workflow from n8n and saves to local repository
- Automatically generates metadata and README files
- Commits changes to Git if auto-commit is enabled

#### Push Workflow
- Select a workflow that exists in the repository
- Press `p` or click "Push" button
- Uploads local workflow to n8n
- Only works for workflows that exist in the local repository

#### Switch Environment
- Press `e` or click "Switch Env" button
- Cycles through Dev → Staging → Prod environments
- Automatically refreshes workflow list and switches Git branch

### Git Operations

#### Git Status Display
- Real-time Git status shown in the top bar
- Shows sync status: `✓ Synced`, `↑N` commits ahead, `↓N` commits behind
- Displays uncommitted changes: staged, modified, untracked files

#### Git Operations
- Press `g` to show detailed Git status
- Press `c` to commit all changes with automatic timestamp
- Press `s` to push commits to GitHub
- Press `f` to fetch/pull latest changes from GitHub

### Search and Filter

Use the search box to filter workflows by:
- Workflow name
- Workflow ID
- Tags

### File Structure

Each workflow is stored in its own directory:
```
workflows/
├── biz/
│   └── {workflow_id}/
│       ├── {sanitized_name}.json    # Workflow definition
│       ├── metadata.json            # Workflow metadata
│       └── README.md                # Generated documentation
└── devops/
    └── {workflow_id}/
        ├── {sanitized_name}.json
        ├── metadata.json
        └── README.md
```

### Configuration Options

Edit `config.yaml` to customize:
- Default environment and workflow directory
- Git settings (auto-commit, author info)
- UI preferences (theme, refresh interval)
- Logging configuration
- Backup settings

## Development

### Running Tests

```bash
pytest tests/
```

### Code Structure

The application follows a clean architecture pattern:

- `main.py`: Main application entry point
- `domain/`: Business logic and models
  - `models.py`: Domain models (Workflow, EnvironmentConfig, etc.)
  - `services.py`: Business services (ApplicationService, WorkflowService, etc.)
- `ui/`: User interface components
  - `screens.py`: Textual screens (WorkflowScreen, HelpScreen)
  - `components.py`: UI components (WorkflowTable, StatusDisplay, GitStatusDisplay)
  - `custom_button.py`: Custom button widget
- `controllers/`: Application controllers
  - `workflow_controller.py`: Handles user interactions and coordinates services
- `scripts/`: Core functionality modules
  - `api.py`: n8n API client with retry logic
  - `git.py`: Git operations manager with full GitHub integration
  - `utils.py`: Utility functions for file handling and README generation

### Adding New Features

1. Create feature branch: `git checkout -b feature/new-feature`
2. Implement changes with tests
3. Run tests: `pytest`
4. Submit pull request

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Check n8n URL and API key in `.env`
   - Verify n8n instance is accessible
   - Check network connectivity

2. **Git Operations Failed**
   - Ensure you're in a Git repository
   - Check Git configuration
   - Verify file permissions

3. **Workflow Not Found**
   - Refresh workflow list with `r`
   - Check if workflow exists in n8n
   - Verify correct environment is selected

4. **Git Push/Pull Issues**
   - Ensure remote repository is configured: `git remote -v`
   - Check if you have push permissions
   - Verify network connectivity to GitHub
   - Check Git status with `g` key to see sync state

### Logging

Logs are written to `logs/app.log` by default. Check this file for detailed error information.

## License

This project is provided as-is for educational and development purposes.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs in `logs/app.log`
3. Create an issue in the repository