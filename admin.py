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
# Vendored dependencies to bundle with the plugin
# These will be downloaded for multiple platforms
VENDORED_PACKAGES = [
    "h3",
]
# Platform tags for wheel downloads (covers most QGIS installations)
WHEEL_PLATFORMS = [
    # Linux
    ("manylinux2014_x86_64", "cp311", "linux"),
    ("manylinux2014_x86_64", "cp312", "linux"),
    ("manylinux2014_x86_64", "cp313", "linux"),
    ("manylinux2014_x86_64", "cp314", "linux"),
    # macOS
    ("macosx_10_9_x86_64", "cp311", "macos-intel"),
    ("macosx_10_9_x86_64", "cp312", "macos-intel"),
    ("macosx_11_0_arm64", "cp311", "macos-arm"),
    ("macosx_11_0_arm64", "cp312", "macos-arm"),
    ("macosx_11_0_arm64", "cp314", "macos-arm"),
    # Windows
    ("win_amd64", "cp311", "windows"),
    ("win_amd64", "cp312", "windows"),
    ("win_amd64", "cp314", "windows"),
]
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


@app.callback()
def main(context: typer.Context, verbose: bool = False, qgis_profile: str = "default"):
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

    # For windows root dir in in AppData
    if os.name == "nt":
        print("User profile:")
        print(os.environ["USERPROFILE"])
        plugin_path = os.path.join(
            "AppData",
            "Roaming",
            "QGIS",
            "QGIS3",
            "profiles",
            "default",
        )
        root_directory = os.environ["USERPROFILE"] + "\\" + plugin_path
    else:
        root_directory = Path.home() / f".local/share/QGIS/QGIS3/profiles/" f"{context.obj['qgis_profile']}"

    base_target_directory = os.path.join(root_directory, "python/plugins", SRC_NAME)
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

    build_path = LOCAL_ROOT_DIR / "build" / SRC_NAME

    root_directory = Path.home() / f".local/share/QGIS/QGIS3/profiles/" f"{context.obj['qgis_profile']}"

    destination_path = root_directory / "python/plugins" / SRC_NAME

    if not os.path.islink(destination_path):
        os.symlink(build_path, destination_path)
    else:
        _log("Symlink already exists, skipping creation.", context=context)


@app.command()
def uninstall(context: typer.Context):
    """Remove the plugin from QGIS plugins directory.

    Args:
        context: Application context.
    """
    root_directory = Path.home() / f".local/share/QGIS/QGIS3/profiles/" f"{context.obj['qgis_profile']}"
    base_target_directory = root_directory / "python/plugins" / SRC_NAME
    shutil.rmtree(str(base_target_directory), ignore_errors=True)
    _log(f"Removed {str(base_target_directory)!r}", context=context)


@app.command()
def generate_zip(
    context: typer.Context,
    version: str = None,
    output_directory: typing.Optional[Path] = LOCAL_ROOT_DIR / "dist",
):
    """Generate plugin zip folder that can be used to install the plugin in QGIS.

    Args:
        context: Application context.
        version: Plugin version.
        output_directory: Directory where the zip folder will be saved.

    Returns:
        Path to the generated zip file.
    """
    build_dir = build(context)
    metadata = _get_metadata()["general"]
    plugin_version = metadata["version"] if version is None else version
    output_directory.mkdir(parents=True, exist_ok=True)
    zip_path = output_directory / f"{SRC_NAME}.{plugin_version}.zip"
    with zipfile.ZipFile(zip_path, "w") as fh:
        _add_to_zip(build_dir, fh, arc_path_base=build_dir.parent)
    typer.echo(f"zip generated at {str(zip_path)!r} " f"on {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    return zip_path


@app.command()
def build(
    context: typer.Context,
    output_directory: typing.Optional[Path] = LOCAL_ROOT_DIR / "build" / SRC_NAME,
    clean: bool = True,
    tests: bool = False,
) -> Path:
    """Build plugin directory for use in QGIS application.

    Args:
        context: Application context.
        output_directory: Build output directory where plugin files will be saved.
        clean: Whether current build directory files should be removed before writing.
        tests: Flag to indicate whether to include test related files.

    Returns:
        Build directory path.
    """
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

    Args:
        output_directory: Output directory where the files will be saved.
        tests: Flag to indicate whether to include test related files.
    """
    output_directory.mkdir(parents=True, exist_ok=True)
    for child in (LOCAL_ROOT_DIR / SRC_NAME).iterdir():
        if child.name != "__pycache__":
            target_path = output_directory / child.name
            handler = shutil.copytree if child.is_dir() else shutil.copy
            handler(str(child.resolve()), str(target_path))
    if tests:
        for child in LOCAL_ROOT_DIR.iterdir():
            if child.name in TEST_FILES:
                target_path = output_directory / child.name
                handler = shutil.copytree if child.is_dir() else shutil.copy
                handler(str(child.resolve()), str(target_path))


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


def _add_to_zip(directory: Path, zip_handler: zipfile.ZipFile, arc_path_base: Path):
    """Add files inside the passed directory to the zip file.

    Args:
        directory: Directory with files that are to be zipped.
        zip_handler: Plugin zip file.
        arc_path_base: Parent directory of the input files directory.
    """
    for item in directory.iterdir():
        if item.is_file():
            zip_handler.write(item, arcname=str(item.relative_to(arc_path_base)))
        else:
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
    base_url = "https://api.github.com/repos/" "worldbank/GEEST/releases"
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


@app.command()
def bundle_deps(
    context: typer.Context,
    output_directory: typing.Optional[Path] = None,
    packages: typing.Optional[str] = None,
):
    """Download and bundle vendored dependencies for all platforms.

    This downloads wheels for the packages listed in VENDORED_PACKAGES
    for multiple platforms (Linux, macOS, Windows) and Python versions,
    then extracts them into the extlibs directory.

    Args:
        context: Application context.
        output_directory: Output directory for extlibs (default: geest/extlibs).
        packages: Comma-separated list of packages to bundle (overrides VENDORED_PACKAGES).
    """
    if output_directory is None:
        output_directory = LOCAL_ROOT_DIR / SRC_NAME / "extlibs"

    output_directory.mkdir(parents=True, exist_ok=True)

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

    for item in extlibs_directory.iterdir():
        if item.name in (".gitkeep", "_wheels"):
            continue
        if item.is_dir():
            shutil.rmtree(item)
            _log(f"Removed {item.name}", context=context)
        elif item.is_file():
            item.unlink()
            _log(f"Removed {item.name}", context=context)

    _log("extlibs cleaned", context=context)


if __name__ == "__main__":
    app()
