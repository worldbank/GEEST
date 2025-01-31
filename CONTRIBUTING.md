# Contributing to GEEST

Thank you for your interest in contributing to GEEST! We appreciate your efforts to improve our project. This document outlines the guidelines and best practices for contributing to the project.

## How to Contribute

You are going to need these prerequisites:

- **Git**: For version control.
- **Python 3.x**: Required for the development and running of the plugin.
- **Nix**: If using NixOS for environment management.
- **QGIS**: The platform to run the plugin.
- **VS Code**: Recommended IDE for development.

### Reporting Bugs

- **Search for existing issues**: Before creating a new bug report, check if the issue has already been reported.
- **Create a detailed issue**: Include a clear description, steps to reproduce the issue, expected behavior, and screenshots if applicable.

### Suggesting Features

- **Discuss your idea**: Open a discussion on the project’s issue tracker or forum to gather feedback before working on a feature.
- **Create a feature request**: Provide a detailed explanation, use cases, and potential impact on the existing functionality.

### Pull Requests

#### Workflow

1. **Fork the repository**: Click the fork button on the repository page.
2. **Clone your fork**: Clone the forked repository to your local machine.

```bash
git clone https://github.com/your-username/GEEST.git
```

Create a branch: Create a new branch for your changes.

```bash
git checkout -b my-feature-branch
```

Make changes: Implement your changes and ensure they follow the project’s coding standards.
Commit your changes: Write a clear and concise commit message.

```bash
git commit -m "Add new feature XYZ"
```

Push your changes: Push the changes to your forked repository.

```bash
git push origin my-feature-branch
```

Open a pull request: Go to the original repository and open a pull request. Include a description of your changes and reference any related issues.

Pull Request Checklist

1. Ensure tests pass: Run all tests locally to confirm they pass.
2. Adhere to coding standards: Ensure your code complies with the project’s coding standards and guidelines.
3. Update documentation: If your change affects documentation, update it accordingly.

Coding Standards

See [CODING.md](CODING.md)

Please also read PRE-COMMIT-README.md



Testing

1. Write tests: Include unit tests for new features or bug fixes.
2. Use pytest: Use the pytest framework for testing.
3. Run tests: Ensure all tests pass before submitting a pull request.

```bash
pytest
```

Compliance

1. Pre-commit hooks: Install and configure pre-commit hooks to enforce coding standards and run tests before committing.
2. GPL-3.0 License: Ensure all contributions comply with the project's GPL-3.0 license.

Setting Up Your Environment

Using NixOS
Create a shell.nix file to define the development environment (see shell.nix)

Using Virtualenv
Create and activate a virtual environment:

Documentation
Update documentation: Ensure new features or changes are documented in the docs/ folder.
Generate documentation: Use MkDocs to generate and serve documentation.

```bash
mkdocs serve
```

Code of Conduct

Please adhere to our Code of Conduct in all interactions.

Questions
If you have any questions or need help, feel free to open an issue or contact us at [project-email@example.com].

Thank you for contributing to GEEST!

## Setting Up the Project

### Cloning the Repository

1. **Fork the repository**: If you haven't already, fork the GEEST repository on GitHub.

2. **Clone your fork**: Clone the forked repository to your local machine.
   
   ```bash
   git clone https://github.com/your-username/GEEST.git
   Add the plugin path: In QGIS, go to Plugins > Manage and Install Plugins > Settings > Plugin Paths and add the path to your GEEST folder.
   ```

Load the plugin: Enable the GEEST plugin from the Installed tab.

Debugging: Use VS Code to set breakpoints and start debugging as configured in the launch configuration.

Packaging the Plugin
Prepare the plugin:

Ensure all necessary files are included.
Update the metadata.txt and __init__.py files with the correct version and author information.
Create a zip package:

bash
Copy code
zip -r GEEST.zip GEEST -x ".*" -x "__pycache__" -x "*.pyc"
Distribute: Share the zip file or upload it to a QGIS plugin repository.

Write Clear Commits: Use descriptive commit messages.
Follow Coding Standards: Ensure your code adheres to the project’s coding standards.
Document Changes: Update documentation for any new features or changes.
Run Tests: Always run tests before pushing changes or making pull requests.
Code Reviews: Participate in code reviews and seek feedback on your contributions.
Questions
For any questions or additional help, please contact the project maintainers or open an issue on GitHub.

Thank you for contributing to GEEST!
