# RastAgent Route Planner

A Python-based agent for route planning and overlay analysis using Google Maps and MCP (Model Context Protocol).

## Project Overview

This tool allows you to:
1.  **Plan Routes**: Fetch optimized routes between two locations using the Google Maps API.
2.  **Analyze Coverage**: Match GPS traces (e.g., from dashcam footage) against a planned route to identify navigation instructions for specific video timestamps.
3.  **Serve via MCP**: Expose these capabilities as tools for an AI agent via the Model Context Protocol.

## Prerequisites

- **Python**: Version 3.10+ (Tested on 3.14.2)
- **Google Maps API Key**: You need a valid API key with the **Directions API** enabled.

## Setup

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd RastAgent
    ```

2.  **Create a Virtual Environment**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuration**:
    Create a `.env` file in the root directory and add your Google Maps API key:
    ```bash
    GOOGLE_MAPS_API_KEY=your_api_key_here
    ```

## Usage

### Running the MCP Server
To start the FastMCP server which exposes the routing tools:

```bash
python3 rast_agent/mcp_server/server.py
```
This will start the server, allowing MCP clients (like Claude Desktop or other agents) to connect and use the `get_google_maps_route` and `analyze_route_coverage` tools.

### Running Tests
To verify the routing logic (using mocks, so no API usage):

```bash
python3 -m unittest tests/test_router_mock.py
```

## Project Structure

- `rast_agent/routing/`: Contains the `GoogleMapsRouter` client.
- `rast_agent/overlay/`: Contains the `RouteMatcher` logic for aligning GPS traces to routes.
- `rast_agent/mcp_server/`: Contains the FastMCP server implementation (`server.py`).
- `route_planning_pipeline.md`: Detailed documentation of the internal workflow.
