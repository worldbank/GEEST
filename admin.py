# -*- coding: utf-8 -*-
"""QGIS plugin admin operations"""

import configparser
import datetime as dt
import json
import os
import shlex
import shutil
import subprocess  # nosec B404
import typing
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import httpx
import typer

LOCAL_ROOT_DIR = Path(__file__).parent.resolve()
SRC_NAME = "geest"
PACKAGE_NAME = SRC_NAME.replace("_", "")
TEST_FILES = ["test", "test_suite.py", "docker-compose.yml", "scripts"]

# Patterns to exclude from build and zip
EXCLUDE_DIRS = {"__pycache__", ".git", ".pytest_cache", "__pypackages__"}
EXCLUDE_EXTENSIONS = {".pyc", ".pyo", ".xcf"}
# Specific dev-only files that have no business in the shipped plugin -
# never imported/opened by any runtime code (confirmed by grepping the
# whole geest/ tree before adding each one here), so excluding them is
# pure size reduction with zero behaviour change. Matched by exact
# filename, not full path - each name is already distinctive enough
# that this can't collide with an unrelated file elsewhere in the tree.
EXCLUDE_FILES = {
    # scripts/import-ods-to-model.sh's dev-time spreadsheet-to-model.json
    # tooling - regenerates geest/resources/model.json, never run by the
    # plugin itself once installed.
    "generate_model.py",
    "geoe3.ods",
    # Design reference, not loaded by any code.
    "geoe3_styling.xlsx",
    # QGIS auto-generates this metadata sidecar when a layer is added to
    # a project during authoring - not read back by the plugin.
    "ghs-mod-2023-tile-scheme.qmd",
    # Unused QGIS Processing model - no code loads it.
    "insights.model3",
}


def _ignore_patterns(directory: str, files: list) -> set:
    """Return set of files/dirs to ignore during shutil.copytree.

    Args:
        directory: The directory being copied.
        files: List of files in the directory.

    Returns:
        Set of filenames to ignore.
    """
    ignored = set()
    for f in files:
        # Ignore excluded directories
        if f in EXCLUDE_DIRS:
            ignored.add(f)
        # Ignore specific dev-only files regardless of extension
        elif f in EXCLUDE_FILES:
            ignored.add(f)
        # Ignore files with excluded extensions
        elif any(f.endswith(ext) for ext in EXCLUDE_EXTENSIONS):
            ignored.add(f)
    return ignored


# Vendored dependencies to bundle with the plugin by default - pinned to
# match requirements-dev.txt's h3==4.4.2 exactly, so the dev env and the
# shipped plugin always carry the identical version. bundle_deps() is
# wired into build()/generate_zip(), so this is bundled automatically,
# not as a separate manual step - see WHEEL_PLATFORMS below for which
# platforms/Python versions get a compiled wheel; the plugin zip has a
# hard 15MB size limit on QGIS's plugin infrastructure (see
# MAX_ZIP_SIZE_MB and the size-check in generate_zip()), so this list is
# deliberately NOT "every package someone might find useful" - it is
# "packages a real indicator/workflow unconditionally needs that aren't
# already in every QGIS Python" (pyarrow, by contrast, is NOT vendored:
# see geest/core/arrow_batch_writer.py's module docstring - it degrades
# gracefully when absent, and OSGeo4W's Windows QGIS already bundles it).
VENDORED_PACKAGES = [
    "h3==4.4.2",
]
# Platform tags for wheel downloads. Deliberately narrow, not "every
# platform/Python combo PyPI has a wheel for" - the 15MB zip limit forced
# a choice (see the "Python versions"/"macOS arch" decision in this
# project's own history):
# - cp312/cp313 only: covers QGIS 3.34 LTR's recent OSGeo4W builds (3.12)
#   and QGIS 4.x (this project's own flake/docker tests run 3.13).
#   cp311 (older QGIS) and cp314 (not yet adopted by any QGIS release)
#   were dropped specifically to fit under the size limit.
# - macOS: arm64 (Apple Silicon) only. h3 publishes no universal2 (fat)
#   wheel, and macOS wheels don't encode architecture in the compiled
#   .so's filename the way manylinux wheels do - so an Intel wheel and an
#   ARM wheel for the same Python version extract to the IDENTICAL path
#   and silently clobber each other. Requesting both is not "extra
#   coverage", it's a bug that silently drops whichever extracts first.
#   Apple Silicon has shipped on every new Mac since 2020.
WHEEL_PLATFORMS = [
    # Linux
    ("manylinux2014_x86_64", "cp312", "linux"),
    ("manylinux2014_x86_64", "cp313", "linux"),
    # macOS (Apple Silicon only - see comment above)
    ("macosx_11_0_arm64", "cp312", "macos-arm"),
    ("macosx_11_0_arm64", "cp313", "macos-arm"),
    # Windows
    ("win_amd64", "cp312", "windows"),
    ("win_amd64", "cp313", "windows"),
]
# Hard limit on QGIS's plugin repository infrastructure - generate_zip()
# refuses to produce a zip over this size.
MAX_ZIP_SIZE_MB = 15
# File patterns/directories inside a bundled wheel that are build-time-only
# (Cython source, C headers, static libs, CMake config) - never needed to
# just `import <package>` at runtime, so bundle_deps() strips them after
# extraction rather than shipping dead weight in every release.
EXTLIBS_BUILD_ARTIFACT_EXTENSIONS = {".pxd", ".pyx", ".h", ".a", ".lib", ".cmake"}
EXTLIBS_BUILD_ARTIFACT_DIRS = {"lib", "lib64", "include"}
EXTLIBS_BUILD_ARTIFACT_FILENAMES = {"CMakeLists.txt"}
app = typer.Typer()


@dataclass
class GithubRelease:
    """
    Class for defining plugin releases details.
    """

    pre_release: bool
    tag_name: str
    url: str
    published_at: dt.datetime


def _get_qgis_profile_dir(profile_name: str) -> Path:
    """Get the QGIS profile directory path, creating it if needed.

    Args:
        profile_name: Name of the QGIS profile.

    Returns:
        Path to the QGIS profile directory.
    """
    if os.name == "nt":
        profile_path = (
            Path(os.environ["USERPROFILE"]) / "AppData" / "Roaming" / "QGIS" / "QGIS3" / "profiles" / profile_name
        )
    else:
        profile_path = Path.home() / ".local" / "share" / "QGIS" / "QGIS3" / "profiles" / profile_name

    # Create the profile directory structure if it doesn't exist
    if not profile_path.exists():
        profile_path.mkdir(parents=True, exist_ok=True)
        # Create the python/plugins directory as well
        (profile_path / "python" / "plugins").mkdir(parents=True, exist_ok=True)

    return profile_path


@app.callback()
def main(context: typer.Context, verbose: bool = False, qgis_profile: str = "GEOE3"):
    """Perform various development-oriented tasks for this plugin.

    Args:
        context: Application context.
        verbose: Whether more details should be displayed.
        qgis_profile: QGIS user profile to be used when operating in QGIS application.
    """
    context.obj = {
        "verbose": verbose,
        "qgis_profile": qgis_profile,
    }


@app.command()
def install(context: typer.Context, build_src: bool = True):
    """Deploy plugin to QGIS plugins directory.

    Args:
        context: Application context.
        build_src: Whether to build plugin files from source.
    """
    _log("Uninstalling...", context=context)
    uninstall(context)
    _log("Building...", context=context)

    built_directory = build(context, clean=True) if build_src else LOCAL_ROOT_DIR / "build" / SRC_NAME

    root_directory = _get_qgis_profile_dir(context.obj["qgis_profile"])
    base_target_directory = root_directory / "python" / "plugins" / SRC_NAME
    _log(f"Copying built plugin to {base_target_directory}...", context=context)
    shutil.copytree(built_directory, base_target_directory)
    _log(
        f"Installed {str(built_directory)!r}" f" into {str(base_target_directory)!r}",
        context=context,
    )


@app.command()
def symlink(context: typer.Context):
    """Create a plugin symlink to QGIS plugins directory.

    Args:
        context: Application context.
    """

    source_path = LOCAL_ROOT_DIR / SRC_NAME

    root_directory = _get_qgis_profile_dir(context.obj["qgis_profile"])
    destination_path = root_directory / "python" / "plugins" / SRC_NAME

    if not os.path.islink(destination_path):
        os.symlink(source_path, destination_path)
        _log(f"Symlink created at {destination_path} to {source_path}", context=context)
    else:
        _log("Symlink already exists, skipping creation.", context=context)
        _log(f"Symlink is at {destination_path}", context=context)


@app.command()
def uninstall(context: typer.Context):
    """Remove the plugin from QGIS plugins directory.

    Args:
        context: Application context.
    """
    root_directory = _get_qgis_profile_dir(context.obj["qgis_profile"])
    base_target_directory = root_directory / "python" / "plugins" / SRC_NAME
    shutil.rmtree(str(base_target_directory), ignore_errors=True)
    _log(f"Removed {str(base_target_directory)!r}", context=context)


@app.command()
def generate_zip(
    context: typer.Context,
    version: str = None,
    output_directory: typing.Optional[Path] = LOCAL_ROOT_DIR / "dist",
    skip_checks: bool = False,
):
    """Generate plugin zip folder that can be used to install the plugin in QGIS.

    Args:
        context: Application context.
        version: Plugin version.
        output_directory: Directory where the zip folder will be saved.
        skip_checks: Skip the pre-flight metadata/published-version checks.

    Returns:
        Path to the generated zip file.
    """
    metadata = _get_metadata()["general"]
    plugin_version = metadata["version"] if version is None else version

    if not skip_checks:
        _run_release_checks(plugin_version, context=context)

    build_dir = build(context)
    output_directory.mkdir(parents=True, exist_ok=True)
    zip_path = output_directory / f"{SRC_NAME}.{plugin_version}.zip"
    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as fh:
        _add_to_zip(build_dir, fh, arc_path_base=build_dir.parent)
    typer.echo(f"zip generated at {str(zip_path)!r} " f"on {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}")

    total_compressed = _print_zip_size_dashboard(zip_path)
    max_bytes = MAX_ZIP_SIZE_MB * 1024 * 1024
    if total_compressed > max_bytes:
        typer.echo(
            f"\n✗ zip is {total_compressed / 1024 / 1024:.2f} MB, over the "
            f"{MAX_ZIP_SIZE_MB} MB hard limit on QGIS's plugin infrastructure. "
            "Trim VENDORED_PACKAGES/WHEEL_PLATFORMS in admin.py or geest/resources before releasing."
        )
        raise typer.Exit(code=1)

    return zip_path


def _print_zip_size_dashboard(zip_path: Path) -> int:
    """Print a small ASCII breakdown of a zip's size by top-level plugin area.

    Groups every entry by the directory immediately under the plugin
    root (geest/extlibs, geest/core, geest/gui, ...; loose files directly
    under the root are grouped as "(root)"), sorted largest-compressed
    first, with a simple bar scaled to the biggest category - so it's
    obvious at a glance what's actually driving the zip toward the 15MB
    limit, not just the final total.

    Args:
        zip_path: Path to the generated plugin zip.

    Returns:
        Total compressed size of the zip, in bytes.
    """
    buckets: typing.Dict[str, typing.Dict[str, int]] = {}
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            parts = Path(info.filename).parts
            category = parts[1] if len(parts) > 2 else "(root)"
            bucket = buckets.setdefault(category, {"compressed": 0, "uncompressed": 0, "files": 0})
            bucket["compressed"] += info.compress_size
            bucket["uncompressed"] += info.file_size
            bucket["files"] += 1

    total_compressed = sum(b["compressed"] for b in buckets.values())
    total_uncompressed = sum(b["uncompressed"] for b in buckets.values())
    total_files = sum(b["files"] for b in buckets.values())
    max_compressed = max((b["compressed"] for b in buckets.values()), default=1) or 1

    bar_width = 30
    inner_width = 68
    rows = sorted(buckets.items(), key=lambda kv: kv[1]["compressed"], reverse=True)

    def _row(content: str) -> str:
        # Defensively truncate rather than let an over-long line blow out
        # the box's right border - every piece here is already sized to
        # fit, but a very long category name or triple-digit MB value
        # should degrade gracefully, not misalign the whole box.
        return f"│ {content[: inner_width - 2]:<{inner_width - 2}} │"

    lines = ["", "┌─ Plugin zip size breakdown " + "─" * (inner_width - 28) + "┐"]
    for category, sizes in rows:
        filled = int(bar_width * sizes["compressed"] / max_compressed)
        bar = "█" * filled + "░" * (bar_width - filled)
        compressed_mb = sizes["compressed"] / 1024 / 1024
        lines.append(_row(f"{category:<12} {bar} {compressed_mb:>6.2f} MB ({sizes['files']:>4} files)"))
    lines.append("├" + "─" * inner_width + "┤")

    max_bytes = MAX_ZIP_SIZE_MB * 1024 * 1024
    status = "within limit" if total_compressed <= max_bytes else "OVER LIMIT"
    mark = "✓" if total_compressed <= max_bytes else "✗"
    lines.append(_row(f"TOTAL: {total_compressed / 1024 / 1024:.2f} MB / {MAX_ZIP_SIZE_MB} MB limit  {mark} {status}"))
    lines.append(_row(f"({total_uncompressed / 1024 / 1024:.2f} MB uncompressed, {total_files} files)"))
    lines.append("└" + "─" * inner_width + "┘")

    typer.echo("\n".join(lines))

    return total_compressed


@app.command()
def build(
    context: typer.Context,
    output_directory: typing.Optional[Path] = LOCAL_ROOT_DIR / "build" / SRC_NAME,
    clean: bool = True,
    tests: bool = False,
    skip_bundle_deps: bool = False,
) -> Path:
    """Build plugin directory for use in QGIS application.

    Args:
        context: Application context.
        output_directory: Build output directory where plugin files will be saved.
        clean: Whether current build directory files should be removed before writing.
        tests: Flag to indicate whether to include test related files.
        skip_bundle_deps: Skip the automatic VENDORED_PACKAGES bundle-deps
            check below (e.g. for a fast local iteration loop that doesn't
            touch network) - never set this for a real release build.

    Returns:
        Build directory path.
    """
    if not skip_bundle_deps:
        _bundle_deps_if_needed(context=context)
    if clean:
        shutil.rmtree(str(output_directory), ignore_errors=True)
    output_directory.mkdir(parents=True, exist_ok=True)
    copy_source_files(output_directory, tests=tests)
    icon_path = copy_icon(output_directory)
    if icon_path is None:
        _log("Could not copy icon", context=context)
    # compile_resources(context, output_directory)
    add_requirements_file(context, output_directory)
    generate_metadata(context, output_directory)
    return output_directory


@app.command()
def copy_icon(
    output_directory: typing.Optional[Path] = LOCAL_ROOT_DIR / "build/temp",
) -> Path:
    """Copy the plugin intended icon to the specified output directory.

    Args:
        output_directory: Output directory where the icon will be saved.

    Returns:
        Icon output directory path, or None if icon not found.
    """

    metadata = _get_metadata()["general"]
    icon_path = LOCAL_ROOT_DIR / "resources" / metadata["icon"]
    if icon_path.is_file():
        target_path = output_directory / icon_path.name
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(icon_path, target_path)
        result = target_path
    else:
        result = None
    return result


@app.command()
def copy_source_files(
    output_directory: typing.Optional[Path] = LOCAL_ROOT_DIR / "build/temp",
    tests: bool = False,
):
    """Copy the plugin source files to the specified output directory.

    Excludes __pycache__, .pyc, .pyo, and .xcf files.

    Args:
        output_directory: Output directory where the files will be saved.
        tests: Flag to indicate whether to include test related files.
    """
    output_directory.mkdir(parents=True, exist_ok=True)
    for child in (LOCAL_ROOT_DIR / SRC_NAME).iterdir():
        if child.name not in EXCLUDE_DIRS:
            target_path = output_directory / child.name
            if child.is_dir():
                shutil.copytree(str(child.resolve()), str(target_path), ignore=_ignore_patterns)
            elif not any(child.name.endswith(ext) for ext in EXCLUDE_EXTENSIONS):
                shutil.copy(str(child.resolve()), str(target_path))
    if tests:
        for child in LOCAL_ROOT_DIR.iterdir():
            if child.name in TEST_FILES:
                target_path = output_directory / child.name
                if child.is_dir():
                    shutil.copytree(str(child.resolve()), str(target_path), ignore=_ignore_patterns)
                elif not any(child.name.endswith(ext) for ext in EXCLUDE_EXTENSIONS):
                    shutil.copy(str(child.resolve()), str(target_path))


@app.command()
def compile_resources(
    context: typer.Context,
    output_directory: typing.Optional[Path] = LOCAL_ROOT_DIR / "build/temp",
):
    """Compile plugin resources using the pyrcc package.

    Args:
        context: Application context.
        output_directory: Output directory where the resources will be saved.
    """
    resources_path = LOCAL_ROOT_DIR / "resources" / "resources.qrc"
    target_path = output_directory / "resources.py"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    _log(f"compile_resources target_path: {target_path}", context=context)
    subprocess.run(shlex.split(f"pyrcc5 -o {target_path} {resources_path}"))  # nosec B603


@app.command()
def add_requirements_file(
    context: typer.Context,
    output_directory: typing.Optional[Path] = LOCAL_ROOT_DIR / "build/temp",
):
    resources_path = LOCAL_ROOT_DIR / "requirements-dev.txt"
    target_path = output_directory / "requirements-dev.txt"

    shutil.copy(str(resources_path.resolve()), str(target_path))


@app.command()
def generate_metadata(
    context: typer.Context,
    output_directory: typing.Optional[Path] = LOCAL_ROOT_DIR / "build/temp",
):
    """Generate plugin metadata file using settings defined in config.json.

    Args:
        context: Application context.
        output_directory: Output directory where the metadata.txt file will be saved.
    """
    metadata = _get_metadata()
    target_path = output_directory / "metadata.txt"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    _log(f"generate_metadata target_path: {target_path}", context=context)
    config = configparser.ConfigParser()
    # do not modify case of parameters, as per
    # https://docs.python.org/3/library/configparser.html#customizing-parser-behaviour
    config.optionxform = lambda option: option
    config["general"] = metadata["general"]
    with target_path.open(mode="w") as fh:
        config.write(fh)


@app.command()
def generate_plugin_repo_xml(
    context: typer.Context,
):
    """Generate the plugin repository xml file for QGIS plugin installation.

    Args:
        context: Application context.

    Returns:
        The generated XML content as a string.
    """
    repo_base_dir = LOCAL_ROOT_DIR / "docs" / "repository"
    repo_base_dir.mkdir(parents=True, exist_ok=True)
    metadata = _get_metadata()["general"]
    fragment_template = """
            <pyqgis_plugin name="{name}" version="{version}">
                <description><![CDATA[{description}]]></description>
                <about><![CDATA[{about}]]></about>
                <version>{version}</version>
                <qgis_minimum_version>{qgis_minimum_version}</qgis_minimum_version>
                <homepage><![CDATA[{homepage}]]></homepage>
                <file_name>{filename}</file_name>
                <icon>{icon}</icon>
                <author_name><![CDATA[{author}]]></author_name>
                <download_url>{download_url}</download_url>
                <update_date>{update_date}</update_date>
                <experimental>{experimental}</experimental>
                <deprecated>{deprecated}</deprecated>
                <tracker><![CDATA[{tracker}]]></tracker>
                <repository><![CDATA[{repository}]]></repository>
                <tags><![CDATA[{tags}]]></tags>
                <server>False</server>
            </pyqgis_plugin>
    """.strip()
    contents = "<?xml version = '1.0' encoding = 'UTF-8'?>\n<plugins>"
    all_releases = _get_existing_releases(context=context)
    _log(f"Found {len(all_releases)} release(s)...", context=context)
    for release in [r for r in _get_latest_releases(all_releases) if r is not None]:
        tag_name = release.tag_name
        _log(f"Processing release {tag_name}...", context=context)
        fragment = fragment_template.format(
            name=metadata.get("name"),
            version=tag_name.replace("v", ""),
            description=metadata.get("description"),
            about=metadata.get("about"),
            qgis_minimum_version=metadata.get("qgisMinimumVersion"),
            homepage=metadata.get("homepage"),
            filename=release.url.rpartition("/")[-1],
            icon=metadata.get("icon", ""),
            author=metadata.get("author"),
            download_url=release.url,
            update_date=release.published_at,
            experimental=release.pre_release,
            deprecated=metadata.get("deprecated"),
            tracker=metadata.get("tracker"),
            repository=metadata.get("repository"),
            tags=metadata.get("tags"),
        )
        contents = "\n".join((contents, fragment))
    contents = "\n".join((contents, "</plugins>"))
    repo_index = repo_base_dir / "plugins.xml"
    repo_index.write_text(contents, encoding="utf-8")
    _log(f"Plugin repo XML file saved at {repo_index}", context=context)

    return contents


@lru_cache()
def _get_metadata() -> typing.Dict:
    """Read the metadata properties from the project configuration file 'config.json'.

    Returns:
        Plugin metadata dictionary.
    """
    config_path = LOCAL_ROOT_DIR / "config.json"
    with config_path.open("r") as fh:
        conf = json.load(fh)
    general_plugin_config = conf["general"]

    general_metadata = general_plugin_config

    general_metadata.update(
        {
            "tags": ", ".join(general_plugin_config.get("tags", [])),
            "changelog": _changelog(),
        }
    )

    metadata = {"general": general_metadata}

    return metadata


def _changelog() -> str:
    """Read the changelog content from a config file.

    Returns:
        Plugin changelog content.
    """
    path = LOCAL_ROOT_DIR / "docs/plugin/changelog.txt"

    with path.open() as fh:
        changelog_file = fh.read()

    return changelog_file


def _metadata_mismatches() -> typing.List[str]:
    """Compare the checked-in metadata.txt against config.json.

    QGIS reads this file directly (e.g. for `admin.py symlink` installs),
    so it must be regenerated whenever config.json changes rather than
    left to drift. The dynamically-generated "changelog" field is excluded
    since it is expected to change on every release and is not sourced
    from config.json.

    Returns:
        Human-readable descriptions of any field that is out of sync;
        empty when metadata.txt matches what `generate-metadata` would
        produce from config.json.
    """
    checked_in_path = LOCAL_ROOT_DIR / SRC_NAME / "metadata.txt"
    if not checked_in_path.is_file():
        return [f"{checked_in_path} does not exist"]

    expected = dict(_get_metadata()["general"])
    expected.pop("changelog", None)

    actual_parser = configparser.ConfigParser()
    actual_parser.optionxform = str
    actual_parser.read(checked_in_path, encoding="utf-8")
    if not actual_parser.has_section("general"):
        return [f"{checked_in_path} has no [general] section"]
    actual = dict(actual_parser["general"])
    actual.pop("changelog", None)

    mismatches = []
    for key, expected_value in expected.items():
        expected_str = str(expected_value)
        actual_str = actual.get(key)
        if actual_str is None:
            mismatches.append(f"{key!r} is missing from {checked_in_path}")
        elif actual_str != expected_str:
            mismatches.append(f"{key!r}: metadata.txt has {actual_str!r}, config.json expects {expected_str!r}")
    return mismatches


def _published_version(package_name: str) -> typing.Optional[str]:
    """Fetch the latest version of this plugin published on plugins.qgis.org.

    Args:
        package_name: The plugin's package/slug name on plugins.qgis.org.

    Returns:
        The latest published version string, or None if it could not be
        determined (plugin not yet published, or no network access).
    """
    url = f"https://plugins.qgis.org/plugins/{package_name}/json"
    try:
        response = httpx.get(url, timeout=10.0)
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        return None
    return response.json().get("latest_version")


def _run_release_checks(plugin_version: str, context: typing.Optional[typer.Context] = None) -> None:
    """Run pre-flight checks before packaging a release zip.

    Verifies that the checked-in metadata.txt matches config.json, and that
    the local version has been bumped past whatever is already published
    on plugins.qgis.org.

    Args:
        plugin_version: The version about to be packaged.
        context: Application context.

    Raises:
        typer.Exit: If either check fails.
    """
    problems = []

    metadata_mismatches = _metadata_mismatches()
    if metadata_mismatches:
        problems.append(
            f"{SRC_NAME}/metadata.txt is out of sync with config.json:\n    - "
            + "\n    - ".join(metadata_mismatches)
            + f"\n  Fix with: python admin.py generate-metadata --output-directory {SRC_NAME}"
        )

    published_version = _published_version(PACKAGE_NAME)
    if published_version is None:
        _log(
            f"Could not determine the published version of {PACKAGE_NAME!r} on plugins.qgis.org "
            "(no network access, or not yet published) — skipping that check.",
            context=context,
        )
    elif published_version == plugin_version:
        problems.append(
            f"version {plugin_version!r} is already published on plugins.qgis.org "
            f"(https://plugins.qgis.org/plugins/{PACKAGE_NAME}/) — bump the version in config.json first."
        )

    if problems:
        typer.echo("Pre-flight checks failed:\n")
        for problem in problems:
            typer.echo(f"✗ {problem}\n")
        typer.echo("Pass --skip-checks to generate-zip to bypass (not recommended for releases).")
        raise typer.Exit(code=1)

    typer.echo(f"✓ metadata.txt is in sync with config.json; version {plugin_version!r} is not yet published.")


def _add_to_zip(directory: Path, zip_handler: zipfile.ZipFile, arc_path_base: Path):
    """Add files inside the passed directory to the zip file.

    Excludes directories and files matching EXCLUDE_DIRS and EXCLUDE_EXTENSIONS.

    Args:
        directory: Directory with files that are to be zipped.
        zip_handler: Plugin zip file.
        arc_path_base: Parent directory of the input files directory.
    """
    for item in directory.iterdir():
        if item.is_file():
            if item.suffix not in EXCLUDE_EXTENSIONS:
                zip_handler.write(item, arcname=str(item.relative_to(arc_path_base)))
        elif item.name not in EXCLUDE_DIRS:
            _add_to_zip(item, zip_handler, arc_path_base)


def _log(msg, *args, context: typing.Optional[typer.Context] = None, **kwargs):
    """Log the message to the terminal.

    Args:
        msg: Message to log.
        *args: Additional positional arguments passed to typer.echo.
        context: Application context.
        **kwargs: Additional keyword arguments passed to typer.echo.
    """
    if context is not None:
        context_user_data = context.obj or {}
        verbose = context_user_data.get("verbose", True)
    else:
        verbose = True
    if verbose:
        typer.echo(msg, *args, **kwargs)


def _get_existing_releases(
    context: typing.Optional = None,
) -> typing.List[GithubRelease]:
    """Get the existing plugin releases available in the Github repository.

    Args:
        context: Application context.

    Returns:
        List of github releases.
    """
    base_url = "https://api.github.com/repos/" "worldbank/GeoE3/releases"
    response = httpx.get(base_url)
    result = []
    if response.status_code == 200:
        payload = response.json()
        for release in payload:
            for asset in release["assets"]:
                if asset.get("content_type") == "application/zip":
                    zip_download_url = asset.get("browser_download_url")
                    break
            else:
                zip_download_url = None
            _log(f"zip_download_url: {zip_download_url}", context=context)
            if zip_download_url is not None:
                result.append(
                    GithubRelease(
                        pre_release=release.get("prerelease", True),
                        tag_name=release.get("tag_name"),
                        url=zip_download_url,
                        published_at=dt.datetime.strptime(release["published_at"], "%Y-%m-%dT%H:%M:%SZ"),
                    )
                )
    return result


def _get_latest_releases(
    current_releases: typing.List[GithubRelease],
) -> typing.Tuple[typing.Optional[GithubRelease], typing.Optional[GithubRelease]]:
    """Search for the latest plugin releases from the Github plugin releases.

    Args:
        current_releases: Existing plugin releases available in the Github repository.

    Returns:
        Tuple containing the latest stable and experimental releases.
    """
    latest_experimental = None
    latest_stable = None
    for release in current_releases:
        if release.pre_release:
            if latest_experimental is not None:
                if release.published_at > latest_experimental.published_at:
                    latest_experimental = release
            else:
                latest_experimental = release
        else:
            if latest_stable is not None:
                if release.published_at > latest_stable.published_at:
                    latest_stable = release
            else:
                latest_stable = release
    return latest_stable, latest_experimental


def _bundle_deps_if_needed(context: typing.Optional[typer.Context] = None) -> None:
    """Call bundle_deps() for VENDORED_PACKAGES, unless every package is already bundled.

    build()'s automatic hook so a plain `generate-zip` always ships
    VENDORED_PACKAGES without a separate manual step - but skips the
    network round-trip entirely once extlibs/ already has the current
    pinned version(s), so repeat local builds stay fast.

    Args:
        context: Application context.
    """
    output_directory = LOCAL_ROOT_DIR / SRC_NAME / "extlibs"
    missing = []
    for pkg_spec in VENDORED_PACKAGES:
        name, _, version = pkg_spec.partition("==")
        marker = output_directory / (f"{name}-{version}.dist-info" if version else f"{name}-")
        if version:
            if not marker.exists():
                missing.append(pkg_spec)
        elif not list(output_directory.glob(f"{name}-*.dist-info")):
            missing.append(pkg_spec)

    if not missing:
        _log(f"extlibs already has {VENDORED_PACKAGES} bundled - skipping bundle-deps", context=context)
        return

    _log(f"Bundling missing vendored dependencies: {missing}", context=context)
    bundle_deps(context, output_directory=output_directory, packages=None)


def _clean_extlibs_dir(extlibs_directory: Path, context: typing.Optional[typer.Context] = None) -> None:
    """Remove every previously-bundled dependency from extlibs_directory, in place.

    Shared by clean_extlibs() and bundle_deps() (which cleans before every
    re-bundle, so switching VENDORED_PACKAGES/WHEEL_PLATFORMS - or just
    re-running after a package version bump - can never leave stale files
    from a previous run's different platform/Python matrix behind).

    Args:
        extlibs_directory: Path to extlibs directory.
        context: Application context.
    """
    if not extlibs_directory.exists():
        return
    for item in extlibs_directory.iterdir():
        if item.name in (".gitkeep", "_wheels"):
            continue
        if item.is_dir():
            shutil.rmtree(item)
            _log(f"Removed {item.name}", context=context)
        elif item.is_file():
            item.unlink()
            _log(f"Removed {item.name}", context=context)


def _strip_extlibs_build_artifacts(output_directory: Path, context: typing.Optional[typer.Context] = None) -> None:
    """Delete build-time-only files a wheel ships but runtime import never needs.

    Cython .pyx/.pxd source, C headers, static libs (.a/.lib), and CMake
    config exist so OTHER packages can compile against a library's C API -
    irrelevant to a QGIS plugin that only ever does `import h3` at
    runtime. Stripping them is pure size reduction with zero behaviour
    change (see EXTLIBS_BUILD_ARTIFACT_EXTENSIONS/_DIRS/_FILENAMES).

    Args:
        output_directory: The extlibs directory just extracted into.
        context: Application context.
    """
    removed_bytes = 0
    for dir_name in EXTLIBS_BUILD_ARTIFACT_DIRS:
        target = output_directory / dir_name
        if target.is_dir():
            removed_bytes += sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
            shutil.rmtree(target)
            _log(f"  Stripped build-only directory: {dir_name}/", context=context)

    for path in output_directory.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix in EXTLIBS_BUILD_ARTIFACT_EXTENSIONS or path.name in EXTLIBS_BUILD_ARTIFACT_FILENAMES:
            removed_bytes += path.stat().st_size
            path.unlink()

    if removed_bytes:
        _log(f"  Stripped {removed_bytes / 1024:.0f} KB of build-only artifacts", context=context)


@app.command()
def bundle_deps(
    context: typer.Context,
    output_directory: typing.Optional[Path] = None,
    packages: typing.Optional[str] = None,
):
    """Download and bundle vendored dependencies for all platforms.

    This downloads wheels for the packages listed in VENDORED_PACKAGES
    for multiple platforms (Linux, macOS, Windows) and Python versions,
    then extracts them into the extlibs directory. Cleans any
    previously-bundled content first, and strips build-time-only files
    (Cython source, C headers, static libs) after extracting - see
    _clean_extlibs_dir()/_strip_extlibs_build_artifacts().

    Args:
        context: Application context.
        output_directory: Output directory for extlibs (default: geest/extlibs).
        packages: Comma-separated list of packages to bundle (overrides VENDORED_PACKAGES).
    """
    if output_directory is None:
        output_directory = LOCAL_ROOT_DIR / SRC_NAME / "extlibs"

    output_directory.mkdir(parents=True, exist_ok=True)
    _clean_extlibs_dir(output_directory, context=context)

    # Use provided packages or default
    pkgs_to_bundle = packages.split(",") if packages else VENDORED_PACKAGES

    _log(f"Bundling dependencies to {output_directory}", context=context)
    _log(f"Packages: {pkgs_to_bundle}", context=context)

    # Create a temp directory for downloading wheels
    temp_wheel_dir = output_directory / "_wheels"
    temp_wheel_dir.mkdir(exist_ok=True)

    try:
        for pkg in pkgs_to_bundle:
            _log(f"\nDownloading {pkg} for all platforms...", context=context)

            for platform_tag, python_tag, platform_name in WHEEL_PLATFORMS:
                _log(f"  - {platform_name} ({python_tag})...", context=context)
                try:
                    result = subprocess.run(  # nosec B603 B607
                        [
                            "pip",
                            "download",
                            "--no-deps",
                            "--only-binary=:all:",
                            f"--platform={platform_tag}",
                            f"--python-version={python_tag[2:]}",  # cp311 -> 311
                            f"--dest={temp_wheel_dir}",
                            pkg,
                        ],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode != 0:
                        _log(f"    Warning: Could not download for {platform_name}/{python_tag}", context=context)
                        _log(f"    {result.stderr}", context=context)
                except subprocess.SubprocessError as e:
                    _log(f"    Error: {e}", context=context)

        # Extract all downloaded wheels
        _log("\nExtracting wheels...", context=context)
        for wheel_file in temp_wheel_dir.glob("*.whl"):
            _log(f"  Extracting {wheel_file.name}", context=context)
            with zipfile.ZipFile(wheel_file, "r") as whl:
                # Extract everything (including .dist-info for metadata)
                whl.extractall(output_directory)

        _log("\nStripping build-only artifacts...", context=context)
        _strip_extlibs_build_artifacts(output_directory, context=context)

        _log(f"\nDependencies bundled to {output_directory}", context=context)

        # List what was extracted
        _log("\nBundled packages:", context=context)
        for item in sorted(output_directory.iterdir()):
            if item.is_dir() and not item.name.startswith("_") and item.name != ".gitkeep":
                _log(f"  - {item.name}", context=context)

    finally:
        # Clean up temp wheel directory
        shutil.rmtree(temp_wheel_dir, ignore_errors=True)


@app.command()
def clean_extlibs(
    context: typer.Context,
    extlibs_directory: typing.Optional[Path] = None,
):
    """Remove all bundled dependencies from extlibs.

    Args:
        context: Application context.
        extlibs_directory: Path to extlibs directory.
    """
    if extlibs_directory is None:
        extlibs_directory = LOCAL_ROOT_DIR / SRC_NAME / "extlibs"

    if not extlibs_directory.exists():
        _log("extlibs directory does not exist", context=context)
        return

    _clean_extlibs_dir(extlibs_directory, context=context)

    _log("extlibs cleaned", context=context)


if __name__ == "__main__":
    app()
