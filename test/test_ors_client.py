import os
import unittest
import json
from geest.core.ors_client import ORSClient


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

    def test_make_request(self):
        """Test the ORSClient with an API request and assert the response is correct."""
        try:
            # Make the actual request to the ORS API
            self.ors.make_request("walking", self.params)

            # Ensure the API key is used and the endpoint is correctly reached
            def check_response(reply):
                # Check if there was an error with the request
                self.assertEqual(
                    reply.error(),
                    reply.NoError,
                    f"Error in network request: {reply.errorString()}",
                )

                # Parse the response and validate the data structure
                response_data = reply.readAll().data().decode()
                response_json = json.loads(response_data)

                # Check that the response contains a 'features' key
                self.assertIn(
                    "features",
                    response_json,
                    "Response does not contain 'features' key",
                )
                self.assertIsInstance(
                    response_json["features"], list, "'features' is not a list"
                )

                # Ensure at least one feature is returned
                self.assertGreater(
                    len(response_json["features"]),
                    0,
                    "No features found in the response",
                )

                # Check that the first feature has the expected structure
                first_feature = response_json["features"][0]
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

                # Ensure the 'coordinates' field is not empty
                self.assertGreater(
                    len(first_feature["geometry"]["coordinates"]),
                    0,
                    "'coordinates' list is empty",
                )

            # Ensure the response handler gets the data and processes it correctly
            reply = self.ors.network_manager.finished.connect(
                lambda: check_response(reply)
            )

        except Exception as e:
            self.fail(f"Test failed due to unexpected exception: {e}")


if __name__ == "__main__":
    unittest.main()
