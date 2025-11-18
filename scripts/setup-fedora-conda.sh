#!/bin/bash
# -*- coding: utf-8 -*-
# setup-fedora-conda.sh
#
# Setup script for GEEST development environment on Fedora with Miniconda
# This script installs all dependencies needed for pre-commit hooks
#
# Prerequisites: Miniconda installed with 'geest' conda environment
# Usage: ./scripts/setup-fedora-conda.sh

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CONDA_ENV_NAME="geest"

# Print functions
print_header() {
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if running on Fedora
check_fedora() {
    if [ ! -f /etc/fedora-release ]; then
        print_warning "This script is designed for Fedora. Continuing anyway..."
    else
        print_success "Running on Fedora: $(cat /etc/fedora-release)"
    fi
}

# Check if conda is installed
check_conda() {
    print_header "Checking Miniconda Installation"

    if ! command -v conda &> /dev/null; then
        print_error "conda command not found!"
        print_info "Please install Miniconda first:"
        echo "  https://docs.conda.io/en/latest/miniconda.html"
        exit 1
    fi

    print_success "Conda is installed: $(conda --version)"
}

# Check if geest conda environment exists
check_conda_env() {
    print_header "Checking Conda Environment"

    if conda env list | grep -q "^${CONDA_ENV_NAME} "; then
        print_success "Conda environment '${CONDA_ENV_NAME}' found"
    else
        print_error "Conda environment '${CONDA_ENV_NAME}' not found!"
        print_info "Please create it first or update CONDA_ENV_NAME in this script"
        exit 1
    fi
}

# Install system dependencies via dnf
install_system_deps() {
    print_header "Installing System Dependencies"

    local packages=(
        "git"
        "ShellCheck"
        "yamllint"
        "nodejs"
        "npm"
    )

    print_info "Checking for missing packages..."
    local missing_packages=()

    for pkg in "${packages[@]}"; do
        if ! rpm -q "$pkg" &> /dev/null; then
            missing_packages+=("$pkg")
        fi
    done

    if [ ${#missing_packages[@]} -eq 0 ]; then
        print_success "All system dependencies already installed"
        return 0
    fi

    print_info "Installing packages: ${missing_packages[*]}"

    if sudo dnf install -y "${missing_packages[@]}"; then
        print_success "System dependencies installed successfully"
    else
        print_error "Failed to install system dependencies"
        exit 1
    fi
}

# Install actionlint (not available in Fedora repos)
install_actionlint() {
    print_header "Installing actionlint"

    if command -v actionlint &> /dev/null; then
        print_success "actionlint already installed: $(actionlint --version)"
        return 0
    fi

    local ACTIONLINT_VERSION="1.7.1"
    local ARCH="linux_amd64"
    local DOWNLOAD_URL="https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/actionlint_${ACTIONLINT_VERSION}_${ARCH}.tar.gz"
    local TEMP_DIR
    TEMP_DIR=$(mktemp -d)

    print_info "Downloading actionlint v${ACTIONLINT_VERSION}..."

    if curl -sL "${DOWNLOAD_URL}" -o "${TEMP_DIR}/actionlint.tar.gz"; then
        tar -xzf "${TEMP_DIR}/actionlint.tar.gz" -C "${TEMP_DIR}"
        sudo mv "${TEMP_DIR}/actionlint" /usr/local/bin/
        sudo chmod +x /usr/local/bin/actionlint
        rm -rf "${TEMP_DIR}"
        print_success "actionlint installed successfully: $(actionlint --version)"
    else
        print_error "Failed to download actionlint"
        rm -rf "${TEMP_DIR}"
        exit 1
    fi
}

# Activate conda environment
activate_conda_env() {
    print_header "Activating Conda Environment"

    print_info "Activating conda environment '${CONDA_ENV_NAME}'..."

    # Source conda.sh to make conda available
    CONDA_BASE=$(conda info --base)
    # shellcheck source=/dev/null
    source "${CONDA_BASE}/etc/profile.d/conda.sh"

    conda activate "${CONDA_ENV_NAME}"
    print_success "Conda environment '${CONDA_ENV_NAME}' activated"
}

# Install Python dependencies
install_python_deps() {
    print_header "Installing Python Dependencies"

    if [ ! -f "requirements-dev.txt" ]; then
        print_error "requirements-dev.txt not found!"
        exit 1
    fi

    print_info "Installing dependencies from requirements-dev.txt..."
    pip install -r requirements-dev.txt

    print_success "Python dependencies installed (includes bandit, black, flake8, etc.)"
}

# Install npm packages (cspell)
install_npm_packages() {
    print_header "Installing NPM Packages"

    if command -v cspell &> /dev/null; then
        print_success "cspell already installed: $(cspell --version)"
    else
        print_info "Installing cspell globally..."
        if sudo npm install -g cspell; then
            print_success "cspell installed successfully: $(cspell --version)"
        else
            print_error "Failed to install cspell"
            exit 1
        fi
    fi
}

# Install pre-commit
install_precommit() {
    print_header "Installing pre-commit"

    print_info "Installing pre-commit package..."
    pip install pre-commit

    print_info "Installing pre-commit hooks..."
    pre-commit install

    print_success "pre-commit installed and hooks configured"
}

# Configure nixfmt skip in bashrc
configure_nixfmt_skip() {
    print_header "Configuring nixfmt Skip"

    local BASHRC="${HOME}/.bashrc"
    local SKIP_LINE="export SKIP=nixfmt  # Skip nixfmt in pre-commit (added by GEEST setup)"

    if grep -q "export SKIP=nixfmt" "${BASHRC}" 2>/dev/null; then
        print_success "SKIP=nixfmt already configured in ~/.bashrc"
    else
        print_info "Adding 'export SKIP=nixfmt' to ~/.bashrc..."
        {
            echo ""
            echo "# GEEST development - skip nixfmt hook (Nix-specific)"
            echo "${SKIP_LINE}"
        } >> "${BASHRC}"
        print_success "Added SKIP=nixfmt to ~/.bashrc"
        print_warning "You'll need to run 'source ~/.bashrc' or restart your shell"
    fi

    # Also export for current session
    export SKIP=nixfmt
    print_info "SKIP=nixfmt set for current session"
}

# Verify installation
verify_installation() {
    print_header "Verifying Installation"

    local tools=(
        "git:Git"
        "shellcheck:ShellCheck"
        "yamllint:yamllint"
        "node:Node.js"
        "npm:NPM"
        "cspell:cspell"
        "actionlint:actionlint"
        "pre-commit:pre-commit"
    )

    local all_ok=true

    # Check Python version
    print_info "Python version: $(python --version)"
    print_info "Conda environment: ${CONDA_ENV_NAME}"

    for tool_spec in "${tools[@]}"; do
        IFS=':' read -r cmd name <<< "$tool_spec"
        if command -v "$cmd" &> /dev/null; then
            print_success "$name is installed"
        else
            print_error "$name is NOT installed"
            all_ok=false
        fi
    done

    # Check Python packages
    local python_packages=(
        "bandit:Bandit (security)"
        "black:Black (formatter)"
        "flake8:Flake8 (linter)"
        "isort:isort (import sorter)"
    )

    for pkg_spec in "${python_packages[@]}"; do
        IFS=':' read -r module name <<< "$pkg_spec"
        if python -c "import ${module}" 2>/dev/null; then
            print_success "$name is installed"
        else
            print_error "$name is NOT installed"
            all_ok=false
        fi
    done

    if [ "$all_ok" = true ]; then
        print_success "All tools verified successfully!"
    else
        print_error "Some tools are missing. Please check the output above."
        return 1
    fi
}

# Test pre-commit hooks
test_precommit() {
    print_header "Testing Pre-commit Hooks"

    print_info "Running pre-commit on all files..."
    print_info "Note: nixfmt will be skipped automatically"
    echo ""

    if pre-commit run --all-files; then
        print_success "All pre-commit hooks passed!"
    else
        print_warning "Some pre-commit hooks failed or made changes."
        print_info "This is normal - review the changes and commit them if appropriate."
        return 0  # Don't fail the script
    fi
}

# Main execution
main() {
    print_header "GEEST Fedora Development Environment Setup"
    echo ""
    print_info "This script sets up the GEEST development environment on Fedora"
    print_info "using Miniconda with the 'geest' conda environment"
    echo ""

    # Store the script directory and change to project root
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    cd "$PROJECT_ROOT" || exit 1

    print_info "Project root: $PROJECT_ROOT"
    echo ""

    # Run setup steps
    check_fedora
    check_conda
    check_conda_env
    install_system_deps
    install_actionlint
    activate_conda_env
    install_python_deps
    install_npm_packages
    install_precommit
    configure_nixfmt_skip
    verify_installation
    test_precommit

    # Final instructions
    print_header "Setup Complete!"
    echo ""
    print_success "Development environment is ready!"
    echo ""
    print_info "Important: Reload your shell configuration:"
    echo "  source ~/.bashrc"
    echo ""
    print_info "Or close and reopen your terminal"
    echo ""
    print_info "Next steps:"
    echo "  1. Activate conda environment: conda activate ${CONDA_ENV_NAME}"
    echo "  2. Run pre-commit manually: pre-commit run --all-files"
    echo "  3. Make a test commit to verify hooks work"
    echo ""
    print_info "The nixfmt hook will be automatically skipped (SKIP=nixfmt is set)"
    echo ""
}

# Run main function
main "$@"
