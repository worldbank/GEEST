#!/usr/bin/env bash
echo "🪛 Running QGIS with the GEEST profile:"
echo "--------------------------------"
echo "Do you want to enable debug mode?"
choice=$(gum choose "🪲 Yes" "🐞 No")
case $choice in
    "🪲 Yes") developer_mode=1 ;;
    "🐞 No") developer_mode=0 ;;
esac
echo "Do you want to enable experimental features?"
choice=$(gum choose "🪲 Yes" "🐞 No")
case $choice in
    "🪲 Yes") GEEST_EXPERIMENTAL=1 ;;
    "🐞 No") GEEST_EXPERIMENTAL=0 ;;
esac

# Running on local used to skip tests that will not work in a local dev env
GEEST_LOG=$HOME/GEEST2.log
rm -f $GEEST_LOG
#nix-shell -p \
#  This is the old way using default nix packages with overrides
#  'qgis.override { extraPythonPackages = (ps: [ ps.pyqtwebengine ps.jsonschema ps.debugpy ps.future ps.psutil ]);}' \
#  --command "GEEST_LOG=${GEEST_LOG} GEEST_DEBUG=${developer_mode} RUNNING_ON_LOCAL=1 qgis --profile GEEST2"

# This is the new way, using Ivan Mincis nix spatial project and a flake
# see flake.nix for implementation details
GEEST_LOG=${GEEST_LOG} \
    GEEST_DEBUG=${developer_mode} \
    GEEST_EXPERIMENTAL=${GEEST_EXPERIMENTAL} \
    RUNNING_ON_LOCAL=1 \
    nix run .#default -- --profile GEEST2
