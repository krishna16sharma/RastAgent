# Route Planning & Overlay Pipeline

This document summarizes the current architecture and workflow for the RastAgent route planning and video overlay system.

## 1. System Overview

The system is designed to fetch routing data from Google Maps and overlay this information (specifically navigation instructions) onto video footage by matching GPS traces from the video to the planned route.

## 2. Architecture Components

### A. Configuration
- **File**: `.env`
- **Purpose**: Stores the `GOOGLE_MAPS_API_KEY` required for authentication.

### B. Routing Engine
- **Component**: `GoogleMapsRouter`
- **Path**: `rast_agent/routing/google_maps_client.py`
- **Functionality**:
  - Wraps the `googlemaps` Python client.
  - Fetches directions between an **origin** and **destination**.
  - Supports multiple travel modes (defaults to "driving", maps "two_wheeler" to available modes).
  - Returns a simplified dictionary containing:
    - Route summary
    - Duration and distance
    - Overview polyline (encoded)
    - Detailed steps (instructions, distance, individual polylines)

### C. Route Matching & Overlay
- **Component**: `RouteMatcher`
- **Path**: `rast_agent/overlay/route_matcher.py`
- **Functionality**:
  - Takes the route data from `GoogleMapsRouter`.
  - **Decodes Polylines**: Converts encoded strings to `(lat, lng)` tuples.
  - **Trace Alignment**:
    - `find_nearest_point`: identifying the closest point on the route for a given GPS coordinate.
    - `get_instruction_for_point`: Logic to determine which specific navigation instruction (e.g., "Turn left at 100ft") corresponds to the user's current location in the GPS trace.
    - *Note*: Currently uses a Euclidean distance heuristic for proximity checks.

### D. Service Layer (MCP)
- **Component**: MCP Server
- **Path**: `rast_agent/mcp_server/server.py`
- **Functionality**:
  - Exposes the internal logic as tools via the Model Context Protocol (FastMCP).
  - **Tools Provided**:
    1.  `get_google_maps_route(origin, destination)`: Returns standard route JSON.
    2.  `analyze_route_coverage(origin, destination, gps_trace)`: High-level workflow that fetches a route and immediately runs the `RouteMatcher` against a provided GPS trace to return an annotated trace with instructions.

## 3. End-to-End Workflow

1.  **Input**:
    - User provides `Origin`, `Destination`, and a `GPS Trace` (series of timestamped lat/lng points from a dashcam video).

2.  **Route Fetching**:
    - The system queries the Google Maps API for the optimal route.

3.  **Trace Analysis**:
    - The system iterates through the input `GPS Trace`.
    - For each point, it calculates the nearest position on the planned route.
    - It identifies the active navigation segment (Step) for that position.
    - It extracts the HTML-free instruction text (e.g., "Head north").

4.  **Output**:
    - A JSON object (or potentially visual overlay) mapping specific timestamps in the video to text-based navigation instructions.

## 4. Current Artifacts
- **Visualization**: `route_visualization.html` (Likely a Leaflet/Folium map rendering the route and points).
- **Testing**: `tests/test_router_mock.py` contains unit tests verifying the router's data parsing logic using mock API responses.
