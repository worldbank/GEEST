#!/usr/bin/env bash

# Run precommit checks
#
RESET='\033[0m'
ORANGE='\033[38;2;237;177;72m'
# Clear screen and show welcome banner
clear
echo -e "$RESET$ORANGE"
chafa geest/resources/geest-banner.png --size=30x80 --colors=256 | sed 's/^/                  /'
# Quick tips with icons
echo -e "$RESET$ORANGE \n__________________________________________________________________\n"
echo "Setting up and running pre-commit hooks..."
echo -e "$RESET$ORANGE \n__________________________________________________________________\n"
pre-commit clean >/dev/null
pre-commit install --install-hooks >/dev/null
pre-commit run --all-files || true
echo -e "$RESET$ORANGE \n__________________________________________________________________\n"
