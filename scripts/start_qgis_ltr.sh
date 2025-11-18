#!/usr/bin/env bash
echo "🪛 Running QGIS with the default profile:"
echo "--------------------------------"

# Set environment variables
GEEST_TEST_DIR="$(pwd)/test" # Set test directory relative to project root

# This is the flake approach, using Ivan Mincis nix spatial project and a flake
# see flake.nix for implementation details
GEEST_LOG=${GEEST_LOG} \
    GEEST_TEST_DIR=${GEEST_TEST_DIR} \
    RUNNING_ON_LOCAL=1 \
    nix run .#qgis-ltr
