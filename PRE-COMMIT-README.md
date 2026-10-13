
# Setting Up Pre-Commit for Python Code Formatting

This repo's `pre-commit` hooks run automatically against all Python files using
`black`, `flake8`, `isort` and more — see `.pre-commit-config.yaml` for the
full list.

## Prerequisites

- `nix develop` (or direnv, via `.envrc`). **Do not `pip install pre-commit`
  or any hook tool directly** — every tool a hook shells out to (`black`,
  `flake8`, `isort`, `end-of-file-fixer`, ...) is provisioned by the flake's
  devShell, and `.pre-commit-config.yaml` only ever uses `repo: local` /
  `language: system` hooks that call those binaries. Hooks must never fetch
  their own copies from PyPI or GitHub.

## Step 1: Enter the dev shell

```bash
nix develop
```

This installs `pre-commit` itself plus every tool its hooks call, and
installs the git hook automatically.

## Step 2: `.pre-commit-config.yaml`

Already present at the repo root. If you add a new hook, add the tool to
`flake.nix`'s `devShells.default` package list first, then wire it up as a
`repo: local` hook with `language: system`, e.g.:

```yaml
- repo: local
  hooks:
    - id: black
      name: "🖤 black"
      entry: black
      language: system
      types: [python]
```

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

This will apply `black` formatting to all Python files in the `geoe3` directory.

## Step 5: Commit Your Changes

Once the hook is installed, every time you make a commit, the `black` formatter will automatically format your Python code within the `geoe3` directory. If any changes are made by `black`, the commit will fail, allowing you to review the changes before committing again.

## Troubleshooting

If you encounter any issues:
1. Make sure `pre-commit` is installed correctly.
2. Ensure your `.pre-commit-config.yaml` file is correctly configured and located in the root of your repository.
3. Check that you have the correct version of `black`.

## Additional Resources

- [Pre-Commit Documentation](https://pre-commit.com/)
- [Black GitHub Repository](https://github.com/psf/black)

---

After following this guide, you will have a working `pre-commit` hook that formats all Python files in the `geoe3` directory using `black` before every commit.

Enjoy coding with consistent formatting! 🚀
