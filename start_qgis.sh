<<<<<<< HEAD
#!/usr/bin/env bash
echo "🪛 Running QGIS with the GEEST profile:"
echo "--------------------------------"

echo "  ___   ____ ___ ____             ____ _____ _____ ____ _____ "
echo " / _ \ / ___|_ _/ ___|           / ___| ____| ____/ ___|_   _|"
echo "| | | | |  _ | |\___ \   _____  | |  _|  _| |  _| \___ \ | |  "
echo "| |_| | |_| || | ___) | |_____| | |_| | |___| |___ ___) || |  "
echo " \__\_\\____|___|____/           \____|_____|_____|____/ |_|  "
                                                              
nix-shell -p \
  'qgis.override { extraPythonPackages = (ps: [ ps.numpy ps.future ps.geopandas ps.rasterio ]);}' \
  --command "qgis --profile GEEST"
