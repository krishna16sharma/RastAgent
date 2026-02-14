import sys
import os
import json
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from rast_agent.routing.google_maps_client import GoogleMapsRouter

def test_live_api():
    load_dotenv()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    
    if not api_key or "your_api_key_here" in api_key:
        print("SKIPPING LIVE TEST: GOOGLE_MAPS_API_KEY not found or default in .env")
        return

    print(f"Testing Live API with key: {api_key[:5]}...")
    
    try:
        router = GoogleMapsRouter()
        # Bangalore Test: GM Palya to Marathahalli
        origin = "KG Colony, GM Palya, C V Raman Nagar, Bangalore"
        destination = "WeWork Roshni Tech Hub, Marathahalli, Bangalore"
        
        print(f"Fetching route from {origin} to {destination}...")
        result = router.get_route(origin, destination, mode="walking")
        
        if "error" in result:
             print(f"API ERROR: {result['error']}")
        else:
             print("SUCCESS: Live Route Fetched!")
             print(f"Duration: {result.get('duration')}")
             print(f"Distance: {result.get('distance')}")
             print(f"Polyline (truncated): {result.get('overview_polyline')[:20]}...")

    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    test_live_api()
