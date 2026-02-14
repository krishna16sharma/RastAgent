# RoadSense (RastAgent)

Road hazard intelligence system for Indian navigation. GoPro dashcam footage + GPS telemetry → Gemini 3 Pro multimodal analysis → severity-coded hazard map with driver advisories.

## Project Context

- **Hackathon**: Gemini 3 Bengaluru Hackathon
- **Core Idea**: Passive, automatic road hazard detection from dashcam footage (zero driver effort)
- **POC Scope**: Post-drive analysis with cached annotations, not live inference
- **Language**: Python 3.10+ (primary), Node.js (GoPro telemetry parsing)

## Architecture

```
GoPro MP4 (video + GPMF telemetry)
  → GPS extraction (utils/gopro-parser.js)
  → Route fetching (rast_agent/routing/google_maps_client.py)
  → Route matching & overlay (rast_agent/overlay/route_matcher.py)
  → Video chunking (15-30s segments, 2-3s overlap)
  → Gemini 3 Pro hazard analysis (structured JSON, per-chunk)
  → GPS mapping (timestamp → lat/lng interpolation)
  → Deduplication (100m proximity radius)
  → Route summary (aggregated Gemini call)
  → Web UI (split-screen: annotated video | Google Maps | route card)
  → MCP server (rast_agent/mcp_server/server.py) exposes tools to AI agents
```

## Key Design Decisions

- **Bounding boxes**: Normalized coordinates (0.0–1.0) for resolution independence
- **Conservative detection bias**: Indian roads are rough by default; only genuinely hazardous conditions flagged. Shadows are not potholes. Parked vehicles are fine.
- **JSON mode**: Gemini returns raw JSON arrays (no wrapping object), empty array `[]` for no hazards
- **Driver advisories**: Every hazard includes an actionable `driver_action` field
- **Post-drive for POC**: Pre-processed + cached, UI reads from cache during demo
- **MCP integration**: Route planning + overlay exposed as FastMCP tools for agent orchestration
- **Euclidean distance heuristic**: Used for route matching MVP; Haversine for production

## Hazard Categories

POTHOLE, SPEED_BREAKER, PEDESTRIAN_ZONE, OVERHEAD_OBSTRUCTION, ROAD_WORK, SHARP_CURVE, SURFACE_CHANGE

## Severity Scale

1=LOW, 2=MODERATE, 3=HIGH, 4=SEVERE, 5=CRITICAL

## Tech Stack

| Component | Technology |
|---|---|
| Video Analysis | Gemini 3 Pro (multimodal, JSON mode) |
| Route Planning | Google Maps Directions API (Python `googlemaps` SDK) |
| Route Matching | Custom `RouteMatcher` with polyline decoding |
| GPS Extraction | gpmf-extract + gopro-telemetry (Node.js) |
| Video Chunking | ffmpeg (CLI) |
| Visualization | Folium (Leaflet maps) |
| Agent Protocol | FastMCP (Model Context Protocol) |
| Voice Alerts | Web Speech API (TTS) |
| Frontend | HTML/JS or React (SPA) |
| Data Format | JSON (cached annotations + route summary) |

## File Structure

```
/
├── CLAUDE.md                          # This file
├── SPEC.json                          # Implementation checklist
├── tasks.json                         # Progress tracker
├── RastAgent.md                       # Full design doc
├── README.md                          # Setup & usage guide
├── requirements.txt                   # Python dependencies
├── route_planning_pipeline.md         # Route pipeline architecture doc
├── route_visualization.html           # Generated Folium map (Leaflet)
├── .env                               # API keys (gitignored)
├── rast_agent/
│   ├── routing/
│   │   └── google_maps_client.py      # GoogleMapsRouter — Directions API wrapper
│   ├── overlay/
│   │   └── route_matcher.py           # RouteMatcher — GPS trace ↔ route alignment
│   └── mcp_server/
│       └── server.py                  # FastMCP server with route + overlay tools
├── tests/
│   ├── test_router_mock.py            # Unit tests (mocked API)
│   ├── test_router_live.py            # Live API integration test
│   ├── test_mcp_local.py              # MCP tool direct invocation test
│   ├── test_mcp_overlay.py            # MCP overlay tool test
│   ├── test_overlay_sim.py            # Overlay simulation with real route
│   └── visualize_route.py             # Folium route visualization script
├── prompts/                           # Gemini prompt templates
├── utils/
│   └── gopro-parser.js                # GoPro GPMF/GPS extraction + video chunking
├── cache/                             # Cached Gemini responses (gitignored)
└── frontend/                          # Web UI (upcoming)
```

## Conventions

- All Gemini responses must conform to the hazard annotation JSON schema defined in RastAgent.md
- GPS samples from GoPro: `{ lat, lon, alt, speed2d, speed3d, date, cts, fix, precision }`
- GPS trace for route matching: `{ lat, lng, timestamp }`
- Video chunks keyed by zero-padded index: `*_chunk_000.mp4`, `*_chunk_001.mp4`, ...
- Cached annotations keyed by chunk index in a single JSON file per drive
- Environment variables for API keys — never commit secrets
- Python virtual environment: `.venv/`
- Use `requirements.txt` for Python deps, `package.json` for Node.js deps

## Commands

```bash
# Python setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run MCP server
python3 rast_agent/mcp_server/server.py

# Run tests
python3 -m unittest tests/test_router_mock.py
python3 tests/test_router_live.py
python3 tests/test_overlay_sim.py

# Visualize route
python3 tests/visualize_route.py

# GoPro GPS extraction (Node.js)
node utils/gopro-parser.js
```

## Progress Tracking

- Check `tasks.json` for current implementation status
- Check `SPEC.json` for the full implementation checklist
