#!/usr/bin/env bash

qgis_setup.sh

# h3 is a load-bearing dependency for local/national H3 grid analyses, and
# defusedxml hardens OSM/Overpass XML parsing - neither is bundled in the
# base QGIS testing image, so install both explicitly before any tests run.
# PIP_BREAK_SYSTEM_PACKAGES is set (rather than passing
# --break-system-packages) because pip on the QGIS 3.34 image is too old to
# recognise that flag; the env var is silently ignored there instead.
PIP_BREAK_SYSTEM_PACKAGES=1 pip3 install --quiet h3==4.4.2 defusedxml==0.7.1

# FIX default installation because the sources must be in "geest" parent folder
rm -rf /root/.local/share/QGIS/QGIS3/profiles/default/python/plugins/geest
ln -sf /tests_directory /root/.local/share/QGIS/QGIS3/profiles/default/python/plugins/geest
ln -sf /tests_directory /usr/share/qgis/python/plugins/geest
