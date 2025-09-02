# NWC Service Provider for LNbits

NWC Service Provider is a **Python extension for LNbits** that enables Lightning wallet connections via the Nostr Wallet Connect (NWC) protocol. This is NOT a standalone application - it's an extension that runs within the LNbits ecosystem.

**Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.**

## Critical Understanding

- **This is an LNbits extension, not a standalone application**
- **Cannot be run independently** - requires LNbits installation and framework
- **Extension-based architecture** - integrates with LNbits wallet management
- **Nostr/Bitcoin Lightning focus** - specialized for cryptocurrency wallet operations

## Working Effectively

### Initial Setup and Dependencies

```bash
# Install Poetry (Python package manager)
pip install poetry

# Install project dependencies (NEVER CANCEL - takes 3-5 minutes)
export PATH="$HOME/.local/bin:$PATH"
cd /path/to/nwcprovider
poetry install --no-root --no-interaction
# Timeout: Set 10+ minutes. Installation downloads many crypto/web dependencies.

# Install frontend dependencies for full build process
poetry run npm i prettier pyright
# Timeout: Set 5+ minutes for npm package installation.
```

### Build and Validation Commands

```bash
# Format code (NEVER CANCEL - takes 3-5 seconds)
make format
# Runs: prettier, black, ruff --fix
# Timeout: Set 2+ minutes to be safe.

# Check code quality (takes 1-2 seconds)
make check
# Runs: mypy, pyright, black --check, ruff check, prettier --check
# Note: Some existing linting issues exist (line length in migrations.py)
# Timeout: Set 2+ minutes.

# Run unit tests (NEVER CANCEL - takes 2-3 seconds)
poetry run pytest tests/unit/ -v
# Fast unit tests - 4 tests covering encryption, signing, method handling
# Timeout: Set 5+ minutes.

# Run all tests including integration (NEVER CANCEL - takes 5+ minutes)
PYTHONUNBUFFERED=1 DEBUG=true poetry run pytest
# Integration tests require Docker and spin up containers
# Timeout: Set 15+ minutes. Integration tests are slow and complex.
```

### Development Workflow

```bash
# Quick validation during development:
poetry run pytest tests/unit/ -v           # Fast unit tests (~2s)
poetry run ruff check . --fix             # Auto-fix linting (~1s)
poetry run black .                        # Format Python code (~1s)

# Full validation before commits:
make format && make check && make test     # Complete pipeline
# Total time: ~8-10 minutes including integration tests
# Timeout: Set 20+ minutes for safety.
```

## Validation Scenarios

**ALWAYS test these scenarios after making changes to ensure functionality:**

### Core Extension Validation

Since this is an LNbits extension, you cannot run it standalone. However, you can validate:

1. **Unit Test Validation** (Required for all changes):

   ```bash
   poetry run pytest tests/unit/test_nwcp.py -v
   ```

   - Tests encryption/decryption between service providers
   - Tests Nostr event signing and verification
   - Tests NWC request/response handling
   - Should complete in under 5 seconds

2. **Code Quality Validation** (Required before commits):

   ```bash
   make format    # Fix formatting issues
   make check     # Verify code quality
   ```

   - All commands should pass except known issues in migrations.py
   - prettier formats HTML/JS/JSON files
   - black formats Python code
   - ruff checks Python style and catches bugs
   - mypy checks type annotations (some existing type issues)

3. **Import and Module Validation**:

   ```bash
   cd /path/to/nwcprovider
   # Test core NWC module (standalone)
   poetry run python -c "import nwcp; print('Core module imports successfully')"

   # Test NWC service provider functionality
   poetry run python -c "
   from nwcp import NWCServiceProvider
   provider = NWCServiceProvider('test_key', '')
   print('NWC Provider created successfully')
   print('Supported methods:', provider.get_supported_methods())
   "

   # Note: tasks.py and crud.py use relative imports and require LNbits context
   # They cannot be imported standalone - this is expected for LNbits extensions
   ```

### Integration Test Validation (Optional - Docker Required)

**WARNING: Integration tests are complex and require Docker. Only run if necessary.**

```bash
# Check Docker availability
docker --version || echo "Docker required for integration tests"

# Run integration tests (NEVER CANCEL - takes 10+ minutes)
cd tests/integration
export HEADLESS=1  # Required for CI environments
bash start.sh      # Starts Docker containers
# Timeout: Set 20+ minutes. Pulls images, starts nostr relay + LNbits
```

## Build and Timing Expectations

### Normal Development Times

- **Poetry dependency install**: 3-5 minutes (first time), 30 seconds (subsequent)
- **npm package install**: 2-3 minutes
- **Unit tests**: 2-3 seconds (4 tests)
- **Code formatting (make format)**: 3-5 seconds
- **Code linting (make check)**: 1-2 seconds
- **Integration tests**: 10-15 minutes (Docker containers + full app testing)

### Timeout Recommendations

**CRITICAL: Use these minimum timeout values to prevent premature cancellation:**

- `poetry install`: 10+ minutes
- `make test` (all tests): 20+ minutes
- `make format`: 2+ minutes
- `make check`: 2+ minutes
- Unit tests only: 5+ minutes
- Integration test setup: 20+ minutes

**NEVER CANCEL build or test commands.** Poetry and Docker operations can take significant time.

## Common Tasks and File Locations

### Key Development Files

```bash
# Main application logic
nwcp.py              # Core NWC service provider implementation
tasks.py             # Background task handling and NWC event processing
crud.py              # Database operations for NWC connections
views_api.py         # REST API endpoints (/api/v1/*)
views.py             # Web UI endpoints (/ and /admin)

# Configuration and dependencies
pyproject.toml       # Poetry dependencies and tool configuration
Makefile             # Development task automation
config.json          # Extension metadata for LNbits
.devcontainer/       # Development environment setup

# Testing
tests/unit/          # Fast unit tests (always run these)
tests/integration/   # Slow Docker-based integration tests
```

### Extension Integration Points

```bash
# LNbits integration
__init__.py          # Extension entry point and task registration
models.py            # Database models using LNbits patterns
migrations.py        # Database schema migrations
permission.py        # NWC permission definitions
```

### Frontend Assets

```bash
# Web interface
templates/nwcprovider/   # HTML templates for user/admin interfaces
static/js/              # JavaScript for web UI
static/image/           # Extension icons and screenshots
```

## Working with the Codebase

### Making Changes

1. **Always run unit tests first**: `poetry run pytest tests/unit/ -v`
2. **Make minimal changes**: This extension has complex crypto/nostr logic
3. **Test crypto functions carefully**: Changes to nwcp.py affect encryption/signing
4. **Validate API changes**: Test both REST endpoints and web interface
5. **Check LNbits integration**: Ensure extension loading still works

### Debugging

```bash
# Enable debug logging
export DEBUG=true
export DEBUG_DATABASE=false  # Avoid log spam

# Test specific functionality
poetry run python -c "
from nwcp import NWCServiceProvider
provider = NWCServiceProvider('test_key', '')
print(provider.get_supported_methods())
"
```

### Before Committing

```bash
# Required validation pipeline
make format     # Auto-fix formatting issues
make check      # Verify code quality
poetry run pytest tests/unit/ -v  # Run fast unit tests

# Full validation (if time allows)
make test       # Includes slow integration tests
```

## Known Issues and Limitations

1. **Linting Issues**: migrations.py has line length violations (expected - auto-generated code)
2. **MyPy Type Issues**: Some missing type annotations in crypto modules
3. **Docker Dependency**: Integration tests require Docker containers
4. **LNbits Coupling**: Cannot run or test standalone - requires LNbits framework
5. **Crypto Dependencies**: Uses secp256k1, nostr protocols - handle with care
6. **Module Import Limitations**: Most modules (tasks.py, crud.py) use relative imports and cannot be imported standalone - this is expected for LNbits extensions. Only nwcp.py can be imported directly.

## Architecture Notes

- **Extension Pattern**: Follows LNbits extension architecture with **init**.py entry point
- **Background Tasks**: Uses LNbits task system for NWC event processing
- **Database**: Integrates with LNbits database using shared models/migrations
- **API Design**: RESTful APIs follow LNbits conventions (/api/v1/ prefix)
- **Frontend**: Server-side rendered HTML with JavaScript enhancements
- **Security**: Implements Nostr cryptographic protocols for wallet connections

## Quick Reference Commands

```bash
# Essential daily commands
export PATH="$HOME/.local/bin:$PATH"          # Enable Poetry
poetry run pytest tests/unit/ -v             # Fast validation
make format                                   # Fix formatting
poetry run ruff check . --fix                # Fix linting

# Pre-commit checklist
make format && make check                     # Quality pipeline
poetry run pytest tests/unit/ -v             # Unit test validation

# Full validation (when needed)
make test                                     # All tests (slow)
```

**Remember**: This is an LNbits extension. Focus on extension integration, API compatibility, and crypto protocol correctness when making changes.
