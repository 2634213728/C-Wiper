# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

C-Wiper is a lightweight Windows system cleaning and C-drive space analysis tool. It compiles Python to a standalone EXE (< 30MB) using Nuitka, features high-performance scanning (100K files in < 60s), and maintains zero false deletions through multi-layer security protection.

## Development Commands

```bash
# Run from source (development)
python main.py

# Run tests
pytest tests/ --cov=src --cov-report=xml
pytest tests/ -v  # Verbose output

# Test individual modules
python -m src.utils.event_bus
python -m src.controllers.state_manager
python -m src.core.security
python -m src.models.scan_result

# Build standalone EXE (requires Nuitka and MSVC Build Tools)
pip install nuitka
python build/compile.py --jobs 4

# Install dependencies
pip install -r requirements.txt
```

## Architecture

### MVC Pattern with Event-Driven Communication

The application follows a strict MVC architecture with an event bus for decoupled communication:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Views     │────▶│ Controllers  │────▶│    Core     │
│  (src/ui/)  │     │(controllers/)│     │  (src/core/)│
└─────────────┘     └──────────────┘     └─────────────┘
       ▲                                       │
       │              ┌─────────────┐          │
       └──────────────│  EventBus   │◀─────────┘
                      │ (utils/)    │
                      └─────────────┘
```

### Key Architectural Components

**EventBus (src/utils/event_bus.py)** - Thread-safe publish-subscribe system
- Singleton pattern with `EventBus.get_instance()`
- All UI updates flow through events: `SCAN_STARTED`, `SCAN_PROGRESS`, `SCAN_COMPLETED`, etc.
- Controllers publish events, Views subscribe to them
- Never directly call UI methods from controllers - always use events

**StateManager (src/controllers/state_manager.py)** - FSM for system state
- States: `IDLE`, `SCANNING`, `CLEANING`, `ANALYZING`
- Thread-safe state transitions with cancellation support
- Controllers must check state before operations
- Prevents concurrent conflicting operations

**SecurityLayer (src/core/security.py)** - Multi-layer protection for file deletion
- **CRITICAL**: All file deletions MUST pass through `SecurityLayer.is_safe_to_delete()`
- Hardcoded protected paths (Windows, Program Files, etc.)
- System files protection (pagefile.sys, hiberfil.sys)
- Path traversal prevention
- Returns `(is_safe: bool, reason: str)` tuple

### Controllers (src/controllers/)

Controllers coordinate between UI and core business logic:

- **ScanController**: Manages file scanning, publishes scan progress events
- **CleanController**: Handles safe file deletion via SecurityLayer
- **AnalysisController**: Performs disk space analysis

All controllers use StateManager for state coordination and EventBus for communication.

### Core Modules (src/core/)

- **scanner.py**: Optimized file scanner with parallel processing
- **cleaner.py**: File deletion operations
- **analyzer.py**: Application space analysis
- **rule_engine.py**: Evaluates files against config/rules.json rules
- **security.py**: Security validation layer

### Data Models (src/models/)

- **ScanTarget**: Defines scan target with path and permissions
- **FileInfo**: Encapsulates file metadata
- **ScanResult**: Complete scan results with statistics

## Rule System

Scan rules are defined in `config/rules.json` with structure:

```json
{
  "id": "unique_id",
  "name": "Display name",
  "conditions": {
    "path_pattern": "*Cache*",      // Glob pattern
    "file_extensions": [".tmp"],    // List of extensions
    "min_size": 1024,               // Bytes
    "max_size": null,
    "name_pattern": "temp*"         // Name wildcard
  },
  "risk_level": "L1_SAFE | L2_REVIEW",
  "category": "temp | logs | browser | system | user",
  "enabled": true
}
```

Risk levels:
- **L1_SAFE**: Safe to delete without confirmation
- **L2_REVIEW**: Requires user confirmation before deletion

## Build System

### Nuitka Compilation

The application compiles to a standalone EXE using Nuitka. The build process:

1. Requires Python 3.10+ and MSVC Build Tools (for C compilation)
2. Compiles to `dist/C-Wiper.exe`
3. CI/CD handled by `.github/workflows/build.yml`

### Build Triggers

- Push to `main` or `develop` branches
- Tags matching `v*` (e.g., `v1.0.0`)
- Manual workflow dispatch

## Security Constraints

When modifying file deletion logic:

1. **ALWAYS** validate through `SecurityLayer.is_safe_to_delete()`
2. **NEVER** bypass security checks for performance
3. **NEVER** add paths to protected list without justification
4. Protected paths are hardcoded in `src/core/security.py`
5. Use `send2trash` for deletion (moves to recycle bin by default)

## UI Development

- Tkinter-based with optional customtkinter for modern styling
- Subscribe to EventBus events in `__init__`
- Unsubscribe in cleanup/destructor to prevent memory leaks
- Run long operations in threads, publish events for UI updates
- Never block the main thread

## Testing

- Target 85%+ coverage for core modules
- Test both success and failure paths for security validations
- Mock file system operations in tests
- Include `if __name__ == "__main__"` test blocks in modules

## Code Standards

- PEP 8 formatting
- Type hints for all function signatures
- Google-style docstrings
- Use `logging` module, never `print()` in production code
- Chinese comments are acceptable (project uses Chinese UI)
