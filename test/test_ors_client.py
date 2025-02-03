import os
import unittest
import json
from qgis.PyQt.QtCore import QEventLoop
from geest.core.ors_client import ORSClient


@unittest.skip("Skip this test for now")
class TestORSClientRealRequest(unittest.TestCase):
    def setUp(self):
        """Ensure the API key is available in the environment before running the test."""
        self.api_key = os.getenv("ORS_API_KEY")
        self.assertIsNotNone(
            self.api_key,
            "API key is missing. Please set the ORS_API_KEY environment variable.",
        )

        # Instantiate the ORSClient
        self.ors = ORSClient("https://api.openrouteservice.org/v2/isochrones")

        # Prepare parameters (for isochrones request)
        self.params = {
            "locations": [[8.681495, 49.41461], [8.687872, 49.420318]],
            "range": [300, 200],
        }

        # Create an event loop for the asynchronous request
        self.loop = QEventLoop()

    def test_make_request(self):
        """Test the ORSClient with an API request and assert the response is correct."""

        def handle_request_finished(response):
            """Handle the signal emitted by ORSClient when the request is finished."""
            try:
                # Ensure the response is not None (check for valid response)
                self.assertIsNotNone(
                    response, "Response is None, indicating an error or empty response."
                )

                # Check that the response contains a 'features' key
                self.assertIn(
                    "features", response, "Response does not contain 'features' key"
                )
                self.assertIsInstance(
                    response["features"], list, "'features' is not a list"
                )

                # Ensure at least one feature is returned
                self.assertGreater(
                    len(response["features"]), 0, "No features found in the response"
                )

                # Check that the first feature has the expected structure
                first_feature = response["features"][0]
                self.assertIn(
                    "geometry", first_feature, "Feature does not contain 'geometry' key"
                )
                self.assertEqual(
                    first_feature["geometry"]["type"],
                    "Polygon",
                    "Expected geometry type 'Polygon'",
                )
                self.assertIn(
                    "coordinates",
                    first_feature["geometry"],
                    "'geometry' does not contain 'coordinates' key",
                )
                self.assertGreater(
                    len(first_feature["geometry"]["coordinates"]),
                    0,
                    "'coordinates' list is empty",
                )
            finally:
                # Stop the event loop after the request finishes
                self.loop.quit()

        # Connect the client's finished signal to the test handler
        self.ors.request_finished.connect(handle_request_finished)

        # Make the actual request to the ORS API
        self.ors.make_request("foot-walking", self.params)

        # Start the event loop to wait for the network request to finish
        self.loop.exec_()


# if __name__ == "__main__":
#    unittest.main()
