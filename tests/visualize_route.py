import sys
import os
import folium
import googlemaps
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from rast_agent.routing.google_maps_client import GoogleMapsRouter

def visualize_route():
    load_dotenv()
    
    # 1. Fetch Route
    router = GoogleMapsRouter()
    origin = "KG Colony, GM Palya, C V Raman Nagar, Bangalore"
    destination = "WeWork Roshni Tech Hub, Marathahalli, Bangalore"
    
    print(f"Fetching route for visualization:\n{origin} -> {destination}")
    route_data = router.get_route(origin, destination, mode="walking")
    
    if "error" in route_data:
        print(f"Error: {route_data['error']}")
        return

    # 2. Extract Polyline
    encoded_polyline = route_data.get("overview_polyline")
    if not encoded_polyline:
        print("No polyline found.")
        return
        
    # 3. Decode Polyline to list of (lat, lng)
    # The googlemaps library has a utility for this, but currently accessible via internal method or external lib.
    # The googlemaps client normally returns the decoded path if requested, but here we have the raw encoded string from our wrapper.
    # We can use the 'polyline' library or googlemaps.convert.decode_polyline
    path = googlemaps.convert.decode_polyline(encoded_polyline)
    # path is list of dicts: [{'lat': x, 'lng': y}, ...]
    
    path_coords = [(p['lat'], p['lng']) for p in path]
    
    if not path_coords:
        print("Could not decode polyline.")
        return

    # 4. Create Map (Centered on start)
    start_coord = path_coords[0]
    m = folium.Map(location=start_coord, zoom_start=13)
    
    # 5. Add Route Line
    folium.PolyLine(
        path_coords,
        color="blue",
        weight=5,
        opacity=0.8,
        tooltip="Google Maps Route"
    ).add_to(m)
    
    # 6. Add Markers
    folium.Marker(path_coords[0], popup=f"Start: {origin}", icon=folium.Icon(color='green')).add_to(m)
    folium.Marker(path_coords[-1], popup=f"End: {destination}", icon=folium.Icon(color='red')).add_to(m)
    
    # 7. Save
    output_file = "route_visualization.html"
    m.save(output_file)
    print(f"Map saved to {os.path.abspath(output_file)}")
    print("Open this file in your browser to see the route.")

if __name__ == "__main__":
    visualize_route()
