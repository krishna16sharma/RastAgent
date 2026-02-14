import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from rast_agent.routing.google_maps_client import GoogleMapsRouter

class TestGoogleMapsRouter(unittest.TestCase):
    @patch('rast_agent.routing.google_maps_client.googlemaps.Client')
    def test_get_route_success(self, MockClient):
        # Setup mock
        mock_instance = MockClient.return_value
        mock_instance.directions.return_value = [{
            "summary": "Fastest route",
            "legs": [{
                "duration": {"text": "15 mins"},
                "distance": {"text": "5 km"},
                "start_address": "Origin",
                "end_address": "Destination",
                "steps": []
            }],
            "overview_polyline": {"points": "encoded_polyline_string"}
        }]

        # Initialize router with dummy key
        router = GoogleMapsRouter(api_key="dummy_key")
        
        # Call method
        result = router.get_route("Origin", "Destination")
        
        # Assertions
        self.assertEqual(result["duration"], "15 mins")
        self.assertEqual(result["distance"], "5 km")
        self.assertEqual(result["overview_polyline"], "encoded_polyline_string")
        mock_instance.directions.assert_called_once()

    @patch('rast_agent.routing.google_maps_client.googlemaps.Client')
    def test_get_route_api_error(self, MockClient):
        # Setup mock to raise exception
        mock_instance = MockClient.return_value
        mock_instance.directions.side_effect = Exception("API Error")
        
        router = GoogleMapsRouter(api_key="dummy_key")
        result = router.get_route("Origin", "Destination")
        
        self.assertIn("error", result)
        self.assertEqual(result["error"], "API Error")

if __name__ == '__main__':
    unittest.main()
