#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generate JSON schema from data."""

__copyright__ = "Copyright 2022, Tim Sutton"
__license__ = "GPL version 3"
__email__ = "tim@kartoza.com"
__revision__ = "$Format:%H$"

# -----------------------------------------------------------
# Copyright (C) 2022 Tim Sutton
# -----------------------------------------------------------
# Licensed under the terms of GNU GPL 3
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# ---------------------------------------------------------------------

import json
import os


def infer_schema(data):
    """Infers the JSON schema from the given JSON data."""
    if isinstance(data, dict):
        properties = {}
        required_keys = []
        for key, value in data.items():
            properties[key] = infer_schema(value)
            required_keys.append(key)
        return {
            "type": "object",
            "properties": properties,
        }
    elif isinstance(data, list):
        if len(data) > 0:
            # Assume the schema of the first element for list items
            return {"type": "array", "items": infer_schema(data[0])}
        else:
            return {"type": "array", "items": {}}
    elif isinstance(data, str):
        return {"type": "string"}
    elif isinstance(data, int):
        return {"type": "integer"}
    elif isinstance(data, float):
        return {"type": "number"}
    elif isinstance(data, bool):
        return {"type": "boolean"}
    elif data is None:
        return {"type": "null"}
    else:
        return {"type": "string"}


def generate_schema_from_json(json_file, schema_file):
    """Generates a schema from a JSON file and writes it to a schema file."""
    # Load the JSON file
    with open(json_file, "r") as f:
        data = json.load(f)

    # Infer the schema
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {"dimensions": infer_schema(data["dimensions"])},
        "required": ["dimensions"],
    }

    # Save the schema to the schema file
    with open(schema_file, "w") as f:
        json.dump(schema, f, indent=4)

    print(f"Schema has been generated and saved to {schema_file}")


# Main function to generate the schema
def main():
    """🔄 Main."""
    # Set default paths
    cwd = os.getcwd()
    model_json_path = os.path.join(cwd, "geest", "resources", "model.json")
    schema_json_path = os.path.join(cwd, "geest", "resources", "schema.json")

    # Check if model.json exists
    if not os.path.exists(model_json_path):
        print(f"Error: {model_json_path} not found.")
        return

    # Generate schema from model.json
    generate_schema_from_json(model_json_path, schema_json_path)


if __name__ == "__main__":
    main()
