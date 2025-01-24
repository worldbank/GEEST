#!/usr/bin/env bash
echo "🪛 Running QGIS with the GEEST profile:"
echo "--------------------------------"
echo "Do you want to enable debug mode?"
choice=$(gum choose "🪲 Yes" "🐞 No" )
case $choice in
	"🪲 Yes") DEBUG_MODE=1 ;;
	"🐞 No") DEBUG_MODE=0 ;;
esac

# Running on local used to skip tests that will not work in a local dev env
nix-shell -p \
  'qgis.override { extraPythonPackages = (ps: [ ps.pyqtwebengine ps.jsonschema ps.debugpy ps.future ps.psutil ]);}' \
  --command "GEEST_DEBUG=${DEBUG_MODE} RUNNING_ON_LOCAL=1 qgis --profile GEEST2"
