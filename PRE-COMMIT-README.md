
# Setting Up Pre-Commit for Python Code Formatting

This guide will walk you through setting up a `pre-commit` hook for automatically formatting all Python files within the `geest` directory using `black`.

## Prerequisites

- **Python 3.x**: Ensure you have Python 3 installed on your machine.
- **pip**: Python's package installer.

## Step 1: Install `pre-commit`

First, you'll need to install the `pre-commit` package. You can do this using `pip`:

```bash
pip install pre-commit
```

## Step 2: Create `.pre-commit-config.yaml`

In the root of your repository, create a file named `.pre-commit-config.yaml`. Add the following configuration to set up `black` as the pre-commit hook for Python code formatting:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.4.0  # Replace with the version of black you are using
    hooks:
      - id: black
        name: black
        language_version: python3
        # Restrict black to only the `geest` directory
        additional_dependencies: []
        args: [geest]
```

- **`repos`**: Defines the hooks to use. Here, we use the `black` formatter from its GitHub repository.
- **`rev`**: Specifies the version of `black`. Make sure to replace it with the version you are using.
- **`args`**: Restricts `black` to format only the Python files within the `geest` directory.

## Step 3: Install the Pre-Commit Hook

Navigate to the root of your repository (where the `.pre-commit-config.yaml` file is located) and install the hook using:

```bash
pre-commit install
```

This command sets up the pre-commit hook so that it will run automatically every time you make a commit.

## Step 4: Run the Hook Manually (Optional)

You can test the hook manually to ensure it works as expected before committing any changes:

```bash
pre-commit run --all-files
```

This will apply `black` formatting to all Python files in the `geest` directory.

## Step 5: Commit Your Changes

Once the hook is installed, every time you make a commit, the `black` formatter will automatically format your Python code within the `geest` directory. If any changes are made by `black`, the commit will fail, allowing you to review the changes before committing again.

## Troubleshooting

If you encounter any issues:
1. Make sure `pre-commit` is installed correctly.
2. Ensure your `.pre-commit-config.yaml` file is correctly configured and located in the root of your repository.
3. Check that you have the correct version of `black`.

## Additional Resources

- [Pre-Commit Documentation](https://pre-commit.com/)
- [Black GitHub Repository](https://github.com/psf/black)

---

After following this guide, you will have a working `pre-commit` hook that formats all Python files in the `geest` directory using `black` before every commit.

Enjoy coding with consistent formatting! 🚀
