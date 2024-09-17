#!/usr/bin/env bash
echo "🪛 Running QGIS with the GEEST profile:"
echo "--------------------------------"
echo "Do you want to enable debug mode?"
choice=$(gum choose "🪲 Yes" "🐞 No" )
case $choice in
	"🪲 Yes") DEBUG_MODE=1 ;;
	"🐞 No") DEBUG_MODE=0 ;;
esac
nix-shell -p \
  'qgis.override { extraPythonPackages = (ps: [ ps.jsonschema ps.debugpy ]);}' \
  --command "GEEST_DEBUG=${DEBUG_MODE} qgis --profile GEEST2"
