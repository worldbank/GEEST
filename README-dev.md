# Developer Guide for GEEST 🚀

Welcome to the GEEST Developer Guide! This document is your one-stop resource for contributing to the project. Whether you're setting up your environment, debugging, or preparing a release, we've got you covered. Let's dive in! 🛠️

---

## Table of Contents 📖

1. [Checking Out the Code](#checking-out-the-code)
2. [Setting Up Your Development Environment](#setting-up-your-development-environment)
3. [Understanding `admin.py`](#understanding-adminpy)
4. [Debugging the Plugin](#debugging-the-plugin)
5. [Making a Patch or Pull Request](#making-a-patch-or-pull-request)
6. [Running Tests](#running-tests)
7. [Tagging a Release](#tagging-a-release)
8. [Coding Standards](#coding-standards)
9. [Credits and Notes](#credits-and-notes)

---

## Checking Out the Code 🧩

### What You'll Learn

In this section, you'll learn how to clone the repository and prepare it for development.

### Steps

1. **Fork the Repository**: Start by forking the GEEST repository on GitHub.
2. **Clone Your Fork**:

   ```bash
   git clone https://github.com/your-username/GEEST.git
   ```

3. **Set Up the Plugin Path**:
   - Open QGIS.
   - Navigate to Plugins > Manage and Install Plugins > Settings > Plugin Paths.
   - Add the path to your local GEEST folder.

---

## Setting Up Your Development Environment 🛠️

### Prerequisites

- Python 3.8 or later
- QGIS 3.22 or later
- `pip` and `virtualenv`

### Steps

1. **Create a Virtual Environment**:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install Dependencies**:

   ```bash
   pip install -r requirements-dev.txt
   ```

---

## Understanding `admin.py` 📜

The `admin.py` script provides various commands for managing the plugin, such as building, installing, and generating metadata.

### Key Commands

- **Build the Plugin**:

   ```bash
   python admin.py build
   ```

- **Install the Plugin**:

   ```bash
   python admin.py install
   ```

- **Generate Metadata**:

   ```bash
   python admin.py generate-metadata
   ```

---

## Debugging the Plugin 🐛

### Steps

1. **Enable Debugging in QGIS**:
   - Go to Settings > Options > System > Environment.
   - Add `PYTHONDEBUG=1`.
2. **Use Logs**:
   - Check the QGIS log panel for messages tagged with `Geest`.

---

## Making a Patch or Pull Request 🔄

### Steps

1. **Create a New Branch**:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes and Commit**:

   ```bash
   git add .
   git commit -m "Describe your changes"
   ```

3. **Push and Create a Pull Request**:

   ```bash
   git push origin feature/your-feature-name
   ```

---

## Running Tests ✅

### Environment Variables

The test system requires the following environment variable:

- **`GEEST_TEST_DIR`**: **Required** - Specifies the path to the test directory. This is automatically set by `scripts/start_qgis.sh` and `scripts/start_qgis_ltr.sh` to point to the project's test directory.

**Important**: The plugin will fail to run tests if this environment variable is not set. Always use the provided startup scripts when developing.

### Steps

1. **Start QGIS with proper environment**:

   ```bash
   # Use one of these scripts to ensure proper environment setup
   ./scripts/start_qgis.sh
   # or
   ./scripts/start_qgis_ltr.sh
   ```

2. **Run Unit Tests from command line**:

   ```bash
   pytest
   ```

3. **Check Code Coverage**:

   ```bash
   pytest --cov=geest
   ```

4. **Run Tests from QGIS Plugin Interface**:
   - Use the "Run Tests" or "Run Single Test" buttons in developer mode
   - Tests will automatically use the `GEEST_TEST_DIR` environment variable

---

## Tagging a Release 🏷️

### Steps

1. **Update `config.json`**:
   - Increment the version number.
2. **Create a Git Tag**:

   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

---

## Coding Standards 🧑‍💻

To ensure consistency and maintainability, please follow the coding standards outlined in the [CODING.md](CODING.md) file. This document provides guidelines on formatting, naming conventions, and best practices for contributing to the GEEST project.

---

## Credits and Notes ✨

- **Maintainers**: Timlinux and Contributors
- **License**: MIT License
