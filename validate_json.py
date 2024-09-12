"""
GEEST Plugin

Author: Your**`validate_json.py`** continued:
GEEST Plugin

Author: Your Name
Copyright: 2024, Your Organization
License: GPL-3.0-only

This file is part of the GEEST QGIS Plugin. It is available under the terms of the GNU General Public License v3.0 only.
See the LICENSE file in the project root for more information.
"""

import json
import jsonschema
from jsonschema import validate, ValidationError, SchemaError
import sys


def load_json_schema(schema_file):
    """
    Loads a JSON schema from a file.

    Args:
        schema_file (str): Path to the schema file.

    Returns:
        dict: JSON schema.
    """
    with open(schema_file, "r") as f:
        return json.load(f)


def validate_json(json_data, schema):
    """
    Validates a JSON document against a schema.

    Args:
        json_data (dict): JSON data to validate.
        schema (dict): JSON schema to validate against.

    Raises:
        ValidationError: If JSON does not conform to the schema.
    """
    validate(instance=json_data, schema=schema)


def main(json_file, schema_file):
    """
    Main function to validate JSON file against a schema.

    Args:
        json_file (str): Path to the JSON file.
        schema_file (str): Path to the schema file.
    """
    try:
        schema = load_json_schema(schema_file)
        with open(json_file, "r") as f:
            json_data = json.load(f)
        validate_json(json_data, schema)
        print(f"{json_file} is valid.")
    except (ValidationError, SchemaError) as e:
        print(f"Validation error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python validate_json.py <json_file> <schema_file>")
    else:
        main(sys.argv[1], sys.argv[2])
