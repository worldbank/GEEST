
# GEEST Coding Guide

This guide outlines coding practices for developing Python code in the GEEST project, including adherence to Python naming conventions, formatting styles, type declarations, and logging mechanisms.

## General Guidelines

- **Consistency**: Ensure consistent naming conventions, formatting, and structure throughout the codebase.
- **Readability**: Code should be clear and easy to read, with well-defined logical flows and separation of concerns.
- **Robustness**: Implement error handling to gracefully manage unexpected situations.

## Naming Conventions

Follow the standard Python naming conventions as defined in [PEP 8](https://peps.python.org/pep-0008/):

- **Variable and Function Names**: Use `snake_case`.
  ```python
  def create_study_area_directory(working_dir: str) -> str:
      ...
  ```
- **Class Names**: Use `PascalCase`.
  ```python
  class StudyAreaProcessor:
      ...
  ```
- **Constants**: Use `UPPER_SNAKE_CASE`.
  ```python
  DEFAULT_EPSG_CODE = 4326
  ```
- **Private Variables and Methods**: Use a leading underscore.
  ```python
  def _calculate_utm_zone(self, bbox: QgsRectangle) -> int:
      ...
  ```

### Exceptions for PyQt Naming Conventions

Follow the standard conventions for PyQt widgets and properties, even when they do not adhere to typical Python naming conventions:
- **Signals and Slots**: Use `camelCase`.
- **PyQt Widget Properties and Methods**: Use the default `camelCase` as provided by PyQt.

Example:
```python
self.layer_combo.layerChanged.connect(self.field_combo.setLayer)
```

## Code Formatting

### Black Formatter

- **Use Black**: All Python code should be formatted with [black](https://black.readthedocs.io/en/stable/), the opinionated code formatter.
- **Configuration**: Use the default line length of 88 characters. This ensures uniform formatting across all files and makes the codebase easier to read and maintain.

To format code with Black:
```bash
black .
```

### Indentation and Spacing

- Use **4 spaces** per indentation level.
- Leave **1 blank line** between functions and class definitions.
- Leave **2 blank lines** before class definitions.

## Type Annotations

### Variable Declarations

- Always declare types for variables, parameters, and return values to enhance code clarity and type safety.

Examples:
```python
def create_study_area_directory(working_dir: str) -> str:
    study_area_dir: str = os.path.join(working_dir, "study_area")
    ...
```
```python
layer: QgsVectorLayer = self.layer_combo.currentLayer()
```

### Function Signatures

- Use type hints for all function parameters and return values.
- If a function does not return any value, use `-> None`.

Example:
```python
def process_study_area(self) -> None:
    ...
```

### Type Imports

- Import types from `typing` where necessary:
    - `Optional`: To indicate optional parameters.
    - `List`, `Dict`, `Tuple`: For more complex types.

Example:
```python
from typing import List, Optional

def save_to_geopackage(features: List[QgsFeature], layer_name: str) -> None:
    ...
```

## Logging

### Use `QgsMessageLog` for Logging

- **Do not use `print()` statements** for debugging or outputting messages.
- Use `QgsMessageLog` for all logging to ensure messages are appropriately directed to QGIS's logging system.

### Standardize Log Tags

- **Tag all messages with `'Geest'`** to allow filtering in the QGIS log.
- Use appropriate log levels:
  - **`Qgis.Info`**: For informational messages.
  - **`Qgis.Warning`**: For warnings that do not interrupt the workflow.
  - **`Qgis.Critical`**: For errors that need immediate attention.

Examples:
```python
QgsMessageLog.logMessage("Created study area grid.", tag="Geest", level=Qgis.Info)
QgsMessageLog.logMessage("Warning: Invalid geometry found.", tag="Geest", level=Qgis.Warning)
QgsMessageLog.logMessage("Error transforming geometry.", tag="Geest", level=Qgis.Critical)
```

## Error Handling

- **Graceful Error Handling**: Always catch exceptions and provide meaningful error messages through `QgsMessageLog`.
- **Use `try`/`except` Blocks**: Wrap code that may raise exceptions in `try`/`except` blocks and log the error.

Example:
```python
try:
    processor.process_study_area()
except Exception as e:
    QgsMessageLog.logMessage(f"Error processing study area: {e}", tag="Geest", level=Qgis.Critical)
```

## GUI Development with PyQt5

- Follow the conventions required by PyQt5, using `camelCase` where necessary for properties and methods.
- Use descriptive variable names for widgets:
  - **`layer_combo`** for `QgsMapLayerComboBox`
  - **`field_combo`** for `QgsFieldComboBox`
  - **`continue_button`** for `QPushButton`
- Maintain a consistent naming pattern throughout the user interface code.

## Code Structure

### Order of Methods

- **Class Methods Order**:
  1. **`__init__` method**
  2. **Public methods** in the order of their usage
  3. **Private (helper) methods** prefixed with `_`

## Comments and Docstrings

### Use Docstrings

- Add docstrings to all functions, classes, and modules using the `"""triple quotes"""` format.
- Include a brief description, parameters, and return values where applicable.

Example:
```python
def select_directory(self) -> None:
    """
    Opens a file dialog to select the working directory and saves it using QSettings.
    """
    ...
```

### Inline Comments

- Use inline comments sparingly and only when necessary to clarify complex logic.
- Use the `#` symbol with a space to start the comment.

Example:
```python
# Transform geometry to the correct CRS once at the start
geom.transform(transform)
```

## Summary Checklist

- **Naming**: Use `snake_case`, `PascalCase`, or `camelCase` as appropriate.
- **Formatting**: Use `black` for consistent code formatting.
- **Type Declarations**: Declare types for all variables and function signatures.
- **Logging**: Use `QgsMessageLog` with the tag `'Geest'`.
- **Error Handling**: Catch and log exceptions appropriately.
- **PyQt5**: Follow PyQt5's conventions for widget naming and handling.
- **Docstrings and Comments**: Use meaningful docstrings and comments to explain the code.

Following these guidelines ensures that code within the GEEST project is clear, consistent, and maintainable.