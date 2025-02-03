#!/usr/bin/env bash

echo "Creating geest/resources/schema.json based on the structure of geest/resources/model.json"

geest/core/generate_schema.py
