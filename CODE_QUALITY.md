# Code Quality with Tox

This project uses [tox](https://tox.readthedocs.io/) for environment management and code quality automation, following patterns from the [OpenShift Virtualization tests project](https://github.com/RedHatQE/openshift-virtualization-tests).

## Available Environments

View all available environments:
```bash
tox list
```

## Quick Commands

### 🚀 Default (Recommended)
```bash
tox
```
- Runs format + lint (the essential checks)
- Safe for everyday use

### 🎨 Format Code
```bash
tox -e format
```
- Removes unused imports and variables with `autoflake`
- Sorts imports with `isort`
- Formats code with `black` (120 character line length)

### 🔍 Lint Code
```bash
tox -e lint
```
- Runs `flake8` linting checks
- Uses 120 character line length
- Ignores E203, W503 (black compatibility)

### 🧹 Quality Check
```bash
tox -e quality
```
- Runs both format and lint in sequence
- Same as default `tox` command

### 🧪 Run Tests
```bash
tox -e test
```
- Runs pytest tests (13 tests pass ✅)
- Includes all necessary dependencies

### 🔍 Type Check (Optional)
```bash
tox -e type-check
```
- Runs `mypy` type checking
- Has some type annotation issues (7 errors)

## Development Workflow

1. **Before committing**, run:
   ```bash
   tox          # Quick format + lint check
   ```

2. **For comprehensive checks**:
   ```bash
   tox -e format,lint,test  # Format, lint, and test
   ```

3. **For specific tasks**:
   ```bash
   tox -e format    # Just format code
   tox -e lint      # Just check linting  
   tox -e test      # Just run tests
   ```

4. **Development environment**:
   ```bash
   tox -e dev       # Set up development environment
   ```

## Configuration

The tox configuration is in `tox.ini` and includes:
- Tool-specific configurations (flake8, isort, pytest)
- Environment isolation
- Dependency management
- Multi-environment testing

## Dependencies

All tools are automatically installed in isolated environments by tox:
- `black` - Code formatter
- `isort` - Import sorter  
- `autoflake` - Unused import remover
- `flake8` - Linter
- `mypy` - Type checker (optional)
- `pytest` - Test runner
