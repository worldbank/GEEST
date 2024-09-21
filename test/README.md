# Testing

To run the tests locally, ensure you have a Python virtual environment and Docker set up.

## Steps to Run Tests

1. **Open Terminal**:
   - Navigate to the root directory of the project.
   - Ensure the files `admin.py` and `run-tests.sh` are present.

2. **Build the Test Directory**:
   - Run the following command in your terminal:
     ```sh
     python admin.py build --tests
     ```
   - This will create a `build` directory with all the project files, including a `test` directory.

3. **Run the Tests**:
   - Execute the script to run the tests:
     ```sh
     ./run-tests.sh
     ```
   - This script will spin up a Docker container to run the tests.
