# GEEST Development Environment Setup

This guide provides comprehensive instructions for setting up your development environment for the GEEST project, including pre-commit hooks, testing, and code quality tools.

## Prerequisites

- Python 3.8 or higher
- QGIS 3.x installed (for running tests)
- Git
- pip

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/worldbank/GEEST.git
cd GEEST
```

### 2. Set Up Python Environment

We recommend using a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### 4. Install Pre-commit Hooks

Pre-commit hooks automatically check your code before each commit:

```bash
pre-commit install
```

To run pre-commit on all files manually:

```bash
pre-commit run --all-files
```

### 5. Set Up direnv (Optional)

The project includes a `.envrc` file for direnv, which automatically activates the environment:

```bash
# Install direnv (on Ubuntu/Debian)
sudo apt-get install direnv

# Add to your shell configuration (~/.bashrc, ~/.zshrc, etc.)
eval "$(direnv hook bash)"  # or zsh, fish, etc.

# Allow the .envrc file
direnv allow
```

## Code Quality Tools

### Flake8 - Python Linting

Flake8 checks for code style issues and potential bugs:

```bash
flake8 geest/
```

Configuration is in `.flake8` file. Key features:
- Line length: 120 characters
- Google-style docstring checking enabled
- Compatible with Black formatter

### Black - Code Formatting

Black automatically formats Python code:

```bash
black geest/
```

Configuration in `pyproject.toml`:
- Line length: 120 characters
- Target: Python 3.8+

### isort - Import Sorting

isort organizes imports:

```bash
isort geest/
```

### darglint - Docstring Linting

darglint checks docstrings for correctness:

```bash
darglint --docstring-style=google geest/
```

## Testing

### Running Tests with pytest

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest test/test_utilities.py

# Run tests with coverage
pytest --cov=geest --cov-report=html

# Run only unit tests (skip slow tests)
pytest -m "not slow"
```

### Running Tests with unittest

The project also supports unittest:

```bash
python test_suite.py
```

### Test Configuration

Test configuration is in `pytest.ini`:
- Test discovery pattern: `test_*.py`
- Test markers: `slow`, `integration`, `unit`
- Qt API: PyQt5

## Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality. The hooks are defined in `.pre-commit-config.yaml` and include:

### Enabled Hooks

1. **End-of-file fixer** - Ensures files end with a newline
2. **Trailing whitespace** - Removes trailing whitespace
3. **YAML/JSON checker** - Validates YAML and JSON files
4. **Black** - Formats Python code
5. **UTF-8 encoding check** - Ensures Python files have UTF-8 pragma
6. **Google docstring check** - Validates docstring format
7. **flake8** - Lints Python code with docstring checking
8. **isort** - Sorts imports
9. **nixfmt** - Formats Nix files
10. **cspell** - Spell checks markdown files
11. **yamllint** - Lints YAML files
12. **actionlint** - Lints GitHub Actions workflows
13. **bandit** - Security analysis for Python
14. **shellcheck** - Lints shell scripts

### Bypassing Pre-commit Hooks

If you need to commit without running hooks (not recommended):

```bash
git commit --no-verify -m "Your commit message"
```

## Code Standards

### UTF-8 Pragma

All Python files must start with the UTF-8 pragma:

```python
# -*- coding: utf-8 -*-
```

### License Header

All Python files must include the license header:

```python
# -*- coding: utf-8 -*-
"""Module description."""

__copyright__ = "Copyright 2022, Tim Sutton"
__license__ = "GPL version 3"
__email__ = "tim@kartoza.com"
__revision__ = "$Format:%H$"

# -----------------------------------------------------------
# Copyright (C) 2022 Tim Sutton
# -----------------------------------------------------------
# Licensed under the terms of GNU GPL 3
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# ---------------------------------------------------------------------
```

### Google-style Docstrings

All functions, classes, and modules must have Google-style docstrings:

```python
def function_name(param1: str, param2: int) -> bool:
    """Brief description of the function.

    Longer description if needed.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: Description of when this error is raised
    """
    pass
```

## Troubleshooting

### Pre-commit Hook Failures

If pre-commit hooks fail:

1. Review the error messages
2. Fix the issues manually or let the hooks auto-fix them
3. Stage the fixed files: `git add .`
4. Commit again: `git commit`

### Test Failures

If tests fail:

1. Check the error messages
2. Ensure QGIS is properly installed
3. Verify all dependencies are installed
4. Run tests with verbose output: `pytest -v`

### Flake8 Docstring Errors

Common docstring errors and fixes:

- **D100**: Missing docstring in public module - Add module docstring at top of file
- **D101**: Missing docstring in public class - Add class docstring
- **D102**: Missing docstring in public method - Add method docstring
- **D103**: Missing docstring in public function - Add function docstring

## Useful Commands

### Update Pre-commit Hooks

```bash
pre-commit autoupdate
```

### Clean Python Cache Files

```bash
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete
```

### Run Specific Pre-commit Hook

```bash
pre-commit run black --all-files
pre-commit run flake8 --all-files
```

## Additional Resources

- [Pre-commit Documentation](https://pre-commit.com/)
- [Black Documentation](https://black.readthedocs.io/)
- [Flake8 Documentation](https://flake8.pycqa.org/)
- [pytest Documentation](https://docs.pytest.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [PEP 8 Style Guide](https://peps.python.org/pep-0008/)

## Contributing

Before submitting a pull request:

1. Ensure all tests pass: `pytest`
2. Ensure code is formatted: `black geest/`
3. Ensure imports are sorted: `isort geest/`
4. Ensure linting passes: `flake8 geest/`
5. Run pre-commit hooks: `pre-commit run --all-files`
6. Update documentation if needed

For more details on coding standards, see [CODING.md](CODING.md).
