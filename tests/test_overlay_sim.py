import sys
import os
import json
import time
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from rast_agent.routing.google_maps_client import GoogleMapsRouter
from rast_agent.overlay.route_matcher import RouteMatcher

def simulate_overlay():
    load_dotenv()
    print("--- Starting Overlay Simulation ---")
    
    # 1. Get Real Route
    router = GoogleMapsRouter()
    origin = "KG Colony, GM Palya, C V Raman Nagar, Bangalore"
    destination = "WeWork Roshni Tech Hub, Marathahalli, Bangalore"
    
    print("Fetching route...")
    route_data = router.get_route(origin, destination, mode="walking")
    
    if "error" in route_data:
        print(f"Error fetching route: {route_data['error']}")
        return

    # 2. Initialize Matcher
    matcher = RouteMatcher(route_data)
    print(f"Route loaded with {len(matcher.polyline_points)} points.")

    # 3. Simulate GPS Stream
    # We will pick a few points along the route + some noise
    test_points = [
        matcher.polyline_points[0], # Start
        matcher.polyline_points[int(len(matcher.polyline_points)/2)], # Middle
        matcher.polyline_points[-1], # End
    ]
    
    print("\n--- Simulating GPS Feed ---")
    for i, pt in enumerate(test_points):
        # Add slight noise to simulate GPS drift
        fake_lat = pt['lat'] + 0.00001
        fake_lng = pt['lng'] - 0.00001
        
        instruction = matcher.get_instruction_for_point(fake_lat, fake_lng)
        nearest = matcher.find_nearest_point(fake_lat, fake_lng)
        
        print(f"Time {i*10}s | GPS: {fake_lat:.5f}, {fake_lng:.5f} | Nearest Route Idx: {nearest['index']} | Instruction: {instruction}")

if __name__ == "__main__":
    simulate_overlay()
