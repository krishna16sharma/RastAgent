import sys
import os
import json
import asyncio
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from rast_agent.mcp_server.server import get_google_maps_route

def test_mcp_tool_direct():
    """
    Test the MCP tool function directly with mocked internal router.
    """
    print("Testing MCP tool 'get_google_maps_route'...")
    
    with patch('rast_agent.mcp_server.server.GoogleMapsRouter') as MockRouter:
        # Setup mock
        mock_instance = MockRouter.return_value
        mock_data = {
            "summary": "Mock Route",
            "duration": "10 mins",
            "distance": "2 km",
            "steps": []
        }
        mock_instance.get_route.return_value = mock_data
        
        # Call the tool function
        result_json = get_google_maps_route("A", "B")
        result = json.loads(result_json)
        
        # Verify
        if result['summary'] == "Mock Route":
             print("SUCCESS: MCP tool returned expected mock data.")
        else:
             print(f"FAILURE: Unexpected result: {result}")

if __name__ == "__main__":
    test_mcp_tool_direct()
