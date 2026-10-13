# GEOE3 Plugin Release Process

## Quick Release Steps

### 1. Update Version in config.json

Before releasing, add a new `Version X.Y.Z - <title>` block at the top of
`docs/plugin/changelog.txt` mirroring the `CHANGELOG.md` `[Unreleased]`
entries — `admin.py` bakes this file (not `CHANGELOG.md`) into the plugin
`metadata.txt` shown in the QGIS Plugin Manager.

Edit `config.json`:

```json
{
  "general": {
    "version": "1.2.3",
    ...
  }
}
```

### 2. Commit and Push Changes

Commit, push and merge changes upstream.

### 3. Pull Latest Changes

Pull latest changes through git.

### 4. Create and Push Tag

```bash
# Create tag (must start with 'v')
git tag -a v1.2.3 -m "Release version 1.2.3"

# Push tag
git push origin v1.2.3
```

### 5. Automated Build

Pushing the tag automatically triggers `.github/workflows/release.yml` which:

- Creates GitHub release
- Generates plugin ZIP
- Uploads ZIP to release
- Updates plugin repository XML

Before packaging, `python admin.py generate-zip` runs two pre-flight checks
and aborts (exit 1) if either fails:

- `geest/metadata.txt` (read directly by QGIS for `symlink` installs) must
  match `config.json` — run `python admin.py generate-metadata
  --output-directory geest` to resync it.
- The version in `config.json` must not already be published at
  https://plugins.qgis.org/plugins/geest/ — a sign the version bump in
  step 1 was missed.

Pass `--skip-checks` to bypass both (not recommended when cutting a real
release).

### 6. Verify

Check release at: https://github.com/worldbank/GEOE3/releases

---
