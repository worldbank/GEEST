# GEEST Development Setup for Fedora (Non-Nix)

This guide provides step-by-step instructions for setting up the GEEST development environment on Fedora Linux using Miniconda, without requiring Nix.

## Prerequisites

- **Fedora Linux** (tested on Fedora 43)
- **Miniconda or Anaconda** installed
- **Git** for version control
- **sudo access** for installing system packages

## Quick Setup (Automated)

We provide an automated setup script that installs all dependencies:

```bash
# Clone the repository (if not already done)
git clone https://github.com/worldbank/GEEST.git
cd GEEST

# Run the automated setup script
./scripts/setup-fedora-conda.sh
```

The script will:
1. Check for Fedora and Miniconda
2. Install system dependencies via dnf
3. Install actionlint manually
4. Activate your `geest` conda environment
5. Install Python dependencies
6. Install npm packages (cspell)
7. Configure pre-commit hooks
8. Add `export SKIP=nixfmt` to ~/.bashrc
9. Verify all installations
10. Run a test of pre-commit hooks

After the script completes, **reload your shell**:

```bash
source ~/.bashrc
```

---

## Manual Setup (Step-by-Step)

If you prefer to set up manually or the automated script fails, follow these steps:

### Step 1: Install System Dependencies

```bash
# Update system
sudo dnf update -y

# Install required system packages
sudo dnf install -y git ShellCheck yamllint nodejs npm
```

### Step 2: Install actionlint

actionlint is not available in Fedora repositories, so install manually:

```bash
# Download and install actionlint
ACTIONLINT_VERSION="1.7.1"
curl -sL "https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/actionlint_${ACTIONLINT_VERSION}_linux_amd64.tar.gz" | tar xz
sudo mv actionlint /usr/local/bin/
sudo chmod +x /usr/local/bin/actionlint

# Verify installation
actionlint --version
```

### Step 3: Set Up Conda Environment

Create and activate the `geest` conda environment:

```bash
# Create conda environment (if not exists)
conda create -n geest python=3.10 -y

# Activate the environment
conda activate geest
```

**Tip:** Add conda activation to your workflow or use `conda activate geest` whenever working on GEEST.

### Step 4: Install Python Dependencies

```bash
# Navigate to project root
cd /path/to/GEEST

# Install development dependencies
pip install -r requirements-dev.txt
```

This installs:
- `black` - Code formatter
- `flake8` - Linter
- `isort` - Import sorter
- `bandit` - Security scanner
- `pre-commit` - Git hook framework
- `pytest` - Testing framework
- And other development tools

### Step 5: Install NPM Packages

Install cspell for spell checking:

```bash
sudo npm install -g cspell
```

### Step 6: Configure Pre-commit

```bash
# Install pre-commit
pip install pre-commit

# Install the git hooks
pre-commit install
```

### Step 7: Handle nixfmt (Nix-Specific Hook)

Since nixfmt is Nix-specific and not needed on Fedora, configure pre-commit to skip it:

```bash
# Add to ~/.bashrc
echo 'export SKIP=nixfmt  # Skip nixfmt in pre-commit (Nix-specific)' >> ~/.bashrc

# Reload bashrc
source ~/.bashrc
```

This tells pre-commit to permanently skip the nixfmt hook.

### Step 8: Verify Installation

Check that all tools are installed:

```bash
# System tools
git --version
shellcheck --version
yamllint --version
node --version
npm --version
cspell --version
actionlint --version

# Python tools (in conda env)
python --version
black --version
flake8 --version
isort --version
pre-commit --version

# Python packages
python -c "import bandit; print('bandit OK')"
```

### Step 9: Test Pre-commit Hooks

Run pre-commit on all files to test:

```bash
# This should skip nixfmt automatically
pre-commit run --all-files
```

You may see some files being reformatted - this is normal. Review the changes.

---

## Pre-commit Hooks Explained

The `.pre-commit-config.yaml` includes these hooks:

### Python Hooks
- **black** - Code formatting (120 char line length)
- **flake8** - Linting (ignores E501 line length)
- **isort** - Import statement sorting
- **bandit** - Security vulnerability scanning

### System Hooks
- **shellcheck** - Shell script linting
- **yamllint** - YAML file linting
- **actionlint** - GitHub Actions workflow linting
- **cspell** - Spell checking for Markdown files

### File Cleanup Hooks
- **end-of-file-fixer** - Ensures files end with newline
- **trailing-whitespace** - Removes trailing whitespace
- **check-yaml** - Validates YAML syntax
- **check-json** - Validates JSON syntax

### Custom Hooks
- **encoding-check** - Ensures UTF-8 encoding in Python files
- **remove-core-file** - Removes core dump files

### Skipped Hooks
- **nixfmt** - Nix code formatter (skipped on Fedora)

---

## Daily Development Workflow

### Activate Environment

Every time you start working on GEEST:

```bash
conda activate geest
cd /path/to/GEEST
```

### Make Changes and Commit

```bash
# Make your code changes
vim geest/core/some_file.py

# Stage changes
git add geest/core/some_file.py

# Commit (pre-commit hooks run automatically)
git commit -m "Add new feature"
```

Pre-commit will:
1. Format code with black
2. Sort imports with isort
3. Check code with flake8
4. Scan for security issues with bandit
5. Run other checks
6. **Skip nixfmt automatically**

If hooks fail or make changes:
- Review the changes
- Stage the reformatted files
- Commit again

### Run Pre-commit Manually

```bash
# Run all hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files

# Run on staged files only
pre-commit run
```

---

## Troubleshooting

### Problem: "nixfmt: command not found"

**Solution:** Ensure `SKIP=nixfmt` is set:
```bash
export SKIP=nixfmt
pre-commit run --all-files
```

Or add to ~/.bashrc permanently.

### Problem: "actionlint: command not found"

**Solution:** Install actionlint manually (see Step 2 above).

### Problem: "cspell: command not found"

**Solution:** Install cspell via npm:
```bash
sudo npm install -g cspell
```

### Problem: Pre-commit hooks fail on first run

**Solution:** This is normal. Pre-commit downloads hook environments on first run. The second run should work.

### Problem: "conda: command not found"

**Solution:** Initialize conda:
```bash
# Find conda installation
~/miniconda3/bin/conda init bash

# Restart shell
exec bash
```

### Problem: Python package import errors

**Solution:** Ensure conda environment is activated:
```bash
conda activate geest
pip install -r requirements-dev.txt
```

---

## Running Tests

```bash
# Activate environment
conda activate geest

# Run all tests
pytest

# Run specific test
pytest test/test_workflow.py

# With coverage
pytest --cov=geest
```

---

## Building and Installing the Plugin

```bash
# Build the plugin
python admin.py build

# Install to QGIS
python admin.py install
```

---

## Additional Resources

- [Pre-commit Documentation](https://pre-commit.com/)
- [Black Code Formatter](https://black.readthedocs.io/)
- [Conda User Guide](https://docs.conda.io/projects/conda/en/latest/user-guide/)
- [GEEST Contributing Guide](CONTRIBUTING.md)
- [Pre-commit Setup Guide](PRE-COMMIT-README.md)

---

## Summary Checklist

- [ ] Fedora system with sudo access
- [ ] Miniconda installed
- [ ] System packages installed (git, ShellCheck, yamllint, nodejs, npm)
- [ ] actionlint installed manually
- [ ] `geest` conda environment created
- [ ] Python dependencies installed from requirements-dev.txt
- [ ] cspell installed via npm
- [ ] pre-commit installed and hooks configured
- [ ] `SKIP=nixfmt` added to ~/.bashrc
- [ ] All tools verified working
- [ ] Pre-commit test run successful

---

## Questions or Issues?

If you encounter problems not covered here:

1. Check the [CONTRIBUTING.md](CONTRIBUTING.md) guide
2. Open an issue on GitHub: https://github.com/worldbank/GEEST/issues
3. Review the pre-commit logs: `.git/hooks/pre-commit`

---

**Happy coding!** 🚀
