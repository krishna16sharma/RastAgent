import sys
import os
import json
import asyncio
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from rast_agent.mcp_server.server import analyze_route_coverage

def test_mcp_overlay():
    load_dotenv()
    print("Testing MCP Tool: analyze_route_coverage...")
    
    origin = "KG Colony, GM Palya, C V Raman Nagar, Bangalore"
    destination = "WeWork Roshni Tech Hub, Marathahalli, Bangalore"
    
    # Simulate a small trace (Start, Middle-ish, End)
    # These are rough coordinates near the expected route
    simulated_trace = [
        {"lat": 12.9723, "lng": 77.6633, "timestamp": 100}, # Near start
        {"lat": 12.9687, "lng": 77.6859, "timestamp": 200}, # Mid
        {"lat": 12.9590, "lng": 77.7000, "timestamp": 300}  # Near end
    ]
    
    print(f"Sending {len(simulated_trace)} points for analysis...")
    
    result_json = analyze_route_coverage(origin, destination, simulated_trace)
    
    if "Error" in result_json and not result_json.startswith("["):
         print(f"FAILED: {result_json}")
         return

    results = json.loads(result_json)
    print(f"Received {len(results)} annotated points.")
    
    for res in results:
        print(f"TS: {res['timestamp']} -> Route Idx: {res['matched_route_index']} | {res['instruction']}")

if __name__ == "__main__":
    test_mcp_overlay()
