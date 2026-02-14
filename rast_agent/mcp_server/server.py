from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import os
import sys

# Ensure the parent directory is in the python path to import the router
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from rast_agent.routing.google_maps_client import GoogleMapsRouter
from rast_agent.overlay.route_matcher import RouteMatcher
from typing import List, Dict

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("rast-agent-router")

@mcp.tool()
def get_google_maps_route(origin: str, destination: str, mode: str = "driving") -> str:
    """
    Get routing directions and polyline between two locations using Google Maps.
    
    Args:
        origin: The starting point address or coordinates.
        destination: The end point address or coordinates.
        mode: The travel mode (driving, walking, bicycling, transit).
    
    Returns:
        A JSON string containing distance, duration, steps, and polyline.
    """
    try:
        router = GoogleMapsRouter()
        route_data = router.get_route(origin, destination, mode)
        import json
        return json.dumps(route_data)
    except Exception as e:
        return f"Error fetching route: {str(e)}"

@mcp.tool()
def analyze_route_coverage(origin: str, destination: str, gps_trace: List[Dict[str, float]]) -> str:
    """
    Analyzes a GPS trace (e.g. from a video) against a calculated route to identify 
    which logical segments/instructions the user was on at each point.
    
    Args:
        origin: Route origin.
        destination: Route destination.
        gps_trace: List of dicts with 'lat', 'lng', and optionally 'timestamp'.
        
    Returns:
        JSON string of the trace points annotated with their matched Route Step Instruction.
    """
    try:
        # 1. Fetch Route (Walking mode hardcoded for Dashcam usecase per user request, or make param)
        router = GoogleMapsRouter()
        route_data = router.get_route(origin, destination, mode="walking")
        
        if "error" in route_data:
             return f"Error fetching route for analysis: {route_data['error']}"
             
        # 2. Match Points
        matcher = RouteMatcher(route_data)
        annotated_trace = []
        
        for point in gps_trace:
            lat = point.get('lat')
            lng = point.get('lng')
            ts = point.get('timestamp', 0)
            
            if lat is None or lng is None:
                continue
                
            instruction = matcher.get_instruction_for_point(lat, lng)
            nearest = matcher.find_nearest_point(lat, lng)
            
            annotated_trace.append({
                "timestamp": ts,
                "original_gps": {"lat": lat, "lng": lng},
                "matched_route_index": nearest['index'] if nearest else -1,
                "instruction": instruction
            })
            
        import json
        return json.dumps(annotated_trace)

    except Exception as e:
        return f"Error analyzing coverage: {str(e)}"


if __name__ == "__main__":
    # This entry point allows running the server directly
    mcp.run()
