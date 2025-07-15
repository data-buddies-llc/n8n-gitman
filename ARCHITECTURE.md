# n8n Workflow Manager - Architecture

## Overview

The n8n Workflow Manager has been refactored into a clean, modular architecture that separates concerns between UI, business logic, and application coordination.

## Project Structure

```
gitman/
├── main.py                 # Application entry point
├── domain/                 # Business logic and models
│   ├── __init__.py
│   ├── models.py          # Domain models and data structures
│   └── services.py        # Business logic services
├── ui/                    # User interface components
│   ├── __init__.py
│   ├── components.py      # Reusable UI components
│   └── screens.py         # Screen definitions
├── controllers/           # Application controllers
│   ├── __init__.py
│   └── workflow_controller.py  # Main workflow controller
└── scripts/               # Utility modules (existing)
    ├── api.py            # n8n API client
    ├── git.py            # Git operations
    └── utils.py          # Utility functions
```

## Architecture Layers

### 1. Domain Layer (`domain/`)

**Purpose**: Contains business logic, domain models, and core services.

**Components**:
- `models.py`: Domain entities like `Workflow`, `EnvironmentConfig`, `ApplicationState`
- `services.py`: Business logic services (`WorkflowService`, `EnvironmentService`, `ApplicationService`)

**Key Classes**:
- `Workflow`: Represents an n8n workflow with metadata
- `WorkflowService`: Handles workflow operations (list, pull, push)
- `EnvironmentService`: Manages environment switching and git branches
- `ApplicationService`: Main orchestrator coordinating other services

### 2. UI Layer (`ui/`)

**Purpose**: Contains all user interface components and screens.

**Components**:
- `components.py`: Reusable UI components (`WorkflowTable`, `StatusDisplay`, `EnvironmentDisplay`)
- `screens.py`: Screen definitions (`WorkflowScreen`, `HelpScreen`)

**Key Features**:
- Clean separation of UI from business logic
- Reusable components for common UI patterns
- Event handling delegated to controllers

### 3. Controller Layer (`controllers/`)

**Purpose**: Coordinates between UI and business logic.

**Components**:
- `workflow_controller.py`: Main controller handling user interactions

**Key Responsibilities**:
- Handles UI events and user actions
- Calls appropriate business services
- Updates UI based on operation results
- Manages async operations

### 4. Infrastructure Layer (`scripts/`)

**Purpose**: External integrations and utilities (existing code).

**Components**:
- `api.py`: n8n API client
- `git.py`: Git repository operations
- `utils.py`: File and workflow utilities

## Design Patterns

### 1. Model-View-Controller (MVC)
- **Model**: Domain models and services
- **View**: UI screens and components
- **Controller**: WorkflowController coordinating between model and view

### 2. Service Layer Pattern
- Business logic encapsulated in service classes
- Clear separation of concerns
- Easier testing and maintenance

### 3. Dependency Injection
- Services receive dependencies through constructors
- Loose coupling between components
- Easier to mock for testing

## Key Benefits

### 1. Separation of Concerns
- UI logic separated from business logic
- Domain models independent of UI framework
- Clear boundaries between layers

### 2. Maintainability
- Each class has a single responsibility
- Easy to locate and modify specific functionality
- Changes in one layer don't affect others

### 3. Testability
- Business logic can be tested independently
- UI components can be tested in isolation
- Mock objects can easily replace dependencies

### 4. Reusability
- UI components can be reused across screens
- Business services can be used by different controllers
- Domain models are framework-agnostic

### 5. Extensibility
- New features can be added without modifying existing code
- New UI screens can reuse existing components
- New business services can be easily integrated

## Usage Example

```python
# Create application service
app_service = ApplicationService()
app_service.initialize('dev')

# Create UI screen
screen = WorkflowScreen(app_service, can_switch_environments=True)

# Create controller
controller = WorkflowController(screen)

# Connect controller to screen actions
screen.action_list_workflows = controller.list_workflows
screen.action_pull_workflow = controller.pull_workflow
```

## Migration from Monolithic Structure

The refactoring maintains full backward compatibility while providing:

1. **Cleaner Code Organization**: Logic moved to appropriate layers
2. **Better Error Handling**: Consistent error handling through `OperationResult`
3. **Improved Testing**: Each component can be tested independently
4. **Enhanced Maintainability**: Changes are localized to specific layers

## Future Enhancements

With this architecture, future enhancements become easier:

1. **New UI Themes**: Modify CSS without touching business logic
2. **Additional Services**: Add new services without modifying existing ones
3. **Testing Suite**: Comprehensive testing of each layer independently
4. **Configuration Management**: Enhanced configuration through domain models
5. **Plugin System**: Easy to add new workflow operations