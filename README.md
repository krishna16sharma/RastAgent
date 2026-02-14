# RoadSense — Road Hazard Intelligence for Indian Navigation

Road hazard detection from GoPro dashcam footage using Gemini 3 Pro multimodal analysis + Google Maps route planning.

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 16+ (for GoPro telemetry parsing)
- ffmpeg, ffprobe (for video processing)
- Google Maps API key
- Gemini API key

### Setup

1. **Clone and install Python dependencies:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Install Node.js dependencies (for GoPro parser):**
   ```bash
   cd utils
   npm install
   cd ..
   ```

3. **Configure environment variables:**
   ```bash
   # .env file created with template
   # Add your API keys:
   GOOGLE_MAPS_API_KEY=your_key_here
   GEMINI_API_KEY=your_key_here
   ```

### Running the App

**Start the Flask server:**
```bash
python server.py
```

Open http://localhost:5000 in your browser.

### Workflow: Analyze a GoPro Video

1. Place your GoPro MP4 in `data/` directory
2. Run: `python -m rast_agent.analysis.pipeline <path_to_video.mp4>`
3. Select report from UI dropdown to view cached results

## Architecture

```
GoPro MP4 → GPS extract → Chunk → Gemini analyze → Map GPS → Dedup → Summary → Cache → UI
```

## Project Structure

```
/
├── .env                           # Environment variables
├── .gitignore                     # Secrets, cache, venv
├── README.md                      # This file
├── requirements.txt               # Python deps
├── server.py                      # Flask server
├── rast_agent/
│   ├── routing/                   # Google Maps integration
│   ├── overlay/                   # Route matching
│   ├── gopro/                     # GoPro pipeline (parser, chunker, interpolator)
│   ├── analysis/                  # Gemini client, pipeline, dedup, mapping
│   └── mcp_server/                # FastMCP tools
├── prompts/                       # Gemini prompt templates
├── frontend/                      # SPA (HTML/CSS/JS)
├── cache/                         # Cached results
├── data/                          # Sample videos
└── tests/                         # Test suite
```

## Hazard Categories

POTHOLE, SPEED_BREAKER, PEDESTRIAN_ZONE, OVERHEAD_OBSTRUCTION, ROAD_WORK, SHARP_CURVE, SURFACE_CHANGE

## Severity: 1=LOW (🟢) to 5=CRITICAL (🔴)

## Key Features

✅ Passive detection from dashcam
✅ Gemini 3 Pro multimodal analysis
✅ Real-time video-map sync + voice alerts
✅ Split-screen annotated UI
✅ Cached results for replay
✅ MCP server for agent integration

## API Endpoints

- `GET /` — SPA
- `GET /api/reports` — List reports
- `GET /api/report/<file>` — Fetch report
- `GET /api/video/<path>` — Serve video
- `GET /api/config` — Frontend config

## MCP Tools

```python
# analyze_video(video_path, chunk_duration, chunk_overlap) → hazards + summary
# get_hazard_report(cache_path) → cached results
# get_google_maps_route(origin, destination, mode) → route
# analyze_route_coverage(origin, destination, gps_trace) → annotated trace
```

## Cost

~$0.50/min for Gemini 3 Pro video = ~$5 for 10-min drive
