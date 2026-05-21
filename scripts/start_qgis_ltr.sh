#!/usr/bin/env bash
echo "🪛 Running QGIS with the GEOE3 profile:"
echo "--------------------------------"
echo "Do you want to enable debug mode?"
choice=$(gum choose "🪲 Yes" "🐞 No")
case $choice in
"🪲 Yes") DEVELOPER_MODE=1 ;;
"🐞 No") DEVELOPER_MODE=0 ;;
esac
echo "Do you want to enable experimental features?"
choice=$(gum choose "🪲 Yes" "🐞 No")
case $choice in
"🪲 Yes") GEOE3_EXPERIMENTAL=1 ;;
"🐞 No") GEOE3_EXPERIMENTAL=0 ;;
esac

# Running on local used to skip tests that will not work in a local dev env
GEOE3_LOG=$HOME/GEOE3.log
GEOE3_TEST_DIR="$(pwd)/test"
rm -f "$GEOE3_LOG"
#nix-shell -p \
#  This is the old way using default nix packages with overrides
#  'qgis.override { extraPythonPackages = (ps: [ ps.pyqtwebengine ps.jsonschema ps.debugpy ps.future ps.psutil ]);}' \
#  --command "GEEST_LOG=${GEEST_LOG} GEEST_DEBUG=${DEVELOPER_MODE} RUNNING_ON_LOCAL=1 qgis --profile GEEST2"

# This is the new way, using Ivan Mincis nix spatial project and a flake
# see flake.nix for implementation details
# Both GEOE3_* and GEEST_* env vars are set for backward compatibility
# QT_QPA_PLATFORM flag forces it to run under x11 protocol
GEOE3_LOG=${GEOE3_LOG} \
  GEOE3_DEBUG=${DEVELOPER_MODE} \
  GEOE3_EXPERIMENTAL=${GEOE3_EXPERIMENTAL} \
  GEOE3_TEST_DIR=${GEOE3_TEST_DIR} \
  RUNNING_ON_LOCAL=1 \
  QT_QPA_PLATFORM=xcb \
  nix run .#qgis-ltr -- --profile GEOE3
