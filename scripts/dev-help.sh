#!/usr/bin/env bash
# SPDX-FileCopyrightText: Tim Sutton
# SPDX-License-Identifier: MIT
#
# Prints the GEOE3 dev-shell banner and a categorised command reference
# covering the full plugin lifecycle. Invoked from flake.nix's devShell
# shellHook, and re-runnable any time via `scripts/dev-help.sh`.

RESET='\033[0m'
BOLD='\033[1m'
CYAN='\033[38;2;83;161;203m'
ORANGE='\033[38;2;237;177;72m'
GRAY='\033[90m'

section() {
  echo -e "\n${BOLD}${ORANGE}$1${RESET}"
}

cmd() {
  printf "   ${GRAY}\xe2\x96\xb6${RESET}  ${CYAN}%-40s${RESET} %s\n" "$1" "$2"
}

clear
echo -e "$RESET$ORANGE"
chafa geest/resources/geoe3-banner.png --size=30x80 --colors=256 | sed 's/^/                  /'
echo -e "$RESET$ORANGE\n__________________________________________________________________\n"
echo -e "   🌈 Your Dev Environment is prepared."

section "🔧  Editor setup"
cmd "./scripts/vscode.sh" "VSCode preconfigured for Python/QGIS dev"
cmd "source .nvim-setup.sh" "Configure Neovim with QGIS/PyQt libs on PYTHONPATH"

section "🚀  Run QGIS"
cmd "scripts/start_qgis.sh" "Launch QGIS 4.x with the GEOE3 profile"
cmd "scripts/start_qgis_ltr.sh" "Launch QGIS LTR 3.44.x with the GEOE3 profile"
cmd "nix run .#qgis" "Same as above, via the nix app"
cmd "nix run .#qgis-ltr" "Same as above (LTR), via the nix app"
cmd "nix run .#qgis_process" "Run qgis_process headless with the GEOE3 profile"

section "🧩  Plugin lifecycle (admin.py)"
cmd "python admin.py build [--tests]" "Build plugin into build/geest"
cmd "python admin.py install" "Build + deploy into the QGIS profile plugins dir"
cmd "python admin.py symlink" "Symlink source tree in for live-reload dev"
cmd "python admin.py uninstall" "Remove plugin from the QGIS profile"
cmd "python admin.py generate-zip" "Checks + build + package -> dist/geest.<version>.zip"
cmd "python admin.py generate-metadata" "Regenerate metadata.txt from config.json"
cmd "python admin.py bundle-deps" "Vendor wheel deps for all platforms into geest/extlibs"
cmd "python admin.py clean-extlibs" "Remove vendored deps from extlibs"
cmd "python admin.py generate-plugin-repo-xml" "Rebuild docs/repository/plugins.xml from releases"

section "✅  Testing"
cmd "scripts/run-tests.sh" "Run suite in qgis/qgis docker (latest + 3.34 LTR)"
cmd "nix run .#test-qgis3" "Same, QGIS 3.34 LTR (Qt5) only"
cmd "nix run .#test-qgis4" "Same, QGIS 4.x (Qt6) only"
cmd "nix run .#test-qgis" "Same, both QGIS versions"

section "🔍  Quality & consistency checks"
cmd "./scripts/checks.sh" "Full pre-commit suite: black, isort, flake8, bandit,"
cmd "" "shellcheck, cspell, nixfmt, yamllint, actionlint..."
cmd "nix flake check" "Validate the flake itself"
cmd "./scripts/run-codeql.sh" "CodeQL static analysis"

section "🧹  Cleanup"
cmd "./scripts/clean.sh" "Remove __pycache__, .venv, core dumps, logs, tmp files"

section "📦  Release"
cmd "see RELEASE_PROCESS.md" "Bump config.json version, tag vX.Y.Z, push ->"
cmd "" "CI builds the zip, publishes the release and repo XML"

echo -e "$RESET$ORANGE\n__________________________________________________________________\n$RESET"
echo -e "   ${GRAY}Show this menu again any time:${RESET} ${CYAN}scripts/dev-help.sh${RESET}\n"
