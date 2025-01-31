#!/usr/bin/env python
import json
import jsonschema
from jsonschema import validate


class JSONValidator:
    def __init__(self, json_schema_path, json_data_path):
        """
        Constructor for the JSONValidator class.
        Takes paths for the JSON schema and the JSON document to be validated.
        """
        self.json_schema_path = json_schema_path
        self.json_data_path = json_data_path
        self.json_schema = self.load_json(json_schema_path)
        self.json_data = self.load_json(json_data_path)

    def load_json(self, file_path):
        """
        Load JSON from the given file path.
        """
        try:
            with open(file_path, "r") as file:
                return json.load(file)
        except Exception as e:
            print(f"Error loading JSON file: {file_path}")
            print(f"Details: {e}")
            return None

    def validate_json(self):
        """
        Validate the JSON data against the JSON schema.
        """
        try:
            # Perform validation
            validate(instance=self.json_data, schema=self.json_schema)
            print("Validation successful: The JSON document is valid.")
        except jsonschema.exceptions.ValidationError as err:
            print("Validation error: The JSON document is invalid.")
            print(f"Error details: {err.message}")


# Example usage:
# validator = JSONValidator('schema.json', 'model.json')
# validator.validate_json()
