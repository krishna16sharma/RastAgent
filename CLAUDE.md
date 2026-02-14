# RoadSense (RastAgent)

Road hazard intelligence system for Indian navigation. GoPro dashcam footage + GPS telemetry → Gemini 3 Pro multimodal analysis → severity-coded hazard map with driver advisories.

## Project Context

- **Hackathon**: Gemini 3 Bengaluru Hackathon
- **Core Idea**: Passive, automatic road hazard detection from dashcam footage (zero driver effort)
- **POC Scope**: Post-drive analysis with cached annotations, not live inference

## Architecture

```
GoPro MP4 (video + GPMF telemetry)
  → GPS extraction (utils/gopro-parser.js)
  → Video chunking (15-30s segments, 2-3s overlap)
  → Gemini 3 Pro analysis (structured JSON, per-chunk)
  → GPS mapping (timestamp → lat/lng interpolation)
  → Deduplication (100m proximity radius)
  → Route summary (aggregated Gemini call)
  → Web UI (split-screen: annotated video | Google Maps | route card)
```

## Key Design Decisions

- **Bounding boxes**: Normalized coordinates (0.0–1.0) for resolution independence
- **Conservative detection bias**: Indian roads are rough by default; only genuinely hazardous conditions flagged
- **JSON mode**: All Gemini responses use structured JSON output, no free-text parsing
- **Driver advisories**: Every hazard includes an actionable `driver_action` field
- **Post-drive for POC**: Pre-processed + cached, UI reads from cache during demo

## Hazard Categories

POTHOLE, SPEED_BREAKER, INFORMAL_JUNCTION, PEDESTRIAN_ZONE, OVERHEAD_OBSTRUCTION, ROAD_WORK, SHARP_CURVE, SURFACE_CHANGE, OBSTRUCTION

## Severity Scale

1=LOW, 2=MODERATE, 3=HIGH, 4=SEVERE, 5=CRITICAL

## Tech Stack

| Component | Technology |
|---|---|
| Video Analysis | Gemini 3 Pro (multimodal, JSON mode) |
| GPS Extraction | gpmf-extract + gopro-telemetry (Node.js) |
| Video Chunking | ffmpeg (CLI) |
| Map Display | Google Maps JavaScript API |
| Voice Alerts | Web Speech API (TTS) |
| Frontend | HTML/JS or React (SPA) |
| Data Format | JSON (cached annotations + route summary) |

## File Structure

```
/
├── CLAUDE.md              # This file
├── SPEC.json              # Implementation checklist
├── tasks.json             # Progress tracker
├── RastAgent.md           # Full design doc
├── utils/
│   └── gopro-parser.js    # GoPro GPMF/GPS extraction + video chunking
├── prompts/               # Gemini prompt templates
├── pipeline/              # Processing pipeline scripts
├── cache/                 # Cached Gemini responses (gitignored)
├── frontend/              # Web UI
└── data/                  # Sample video/GPS data (gitignored)
```

## Conventions

- All Gemini responses must conform to the hazard annotation JSON schema defined in RastAgent.md
- GPS samples: `{ lat, lon, alt, speed2d, speed3d, date, cts, fix, precision }`
- Video chunks keyed by zero-padded index: `*_chunk_000.mp4`, `*_chunk_001.mp4`, ...
- Cached annotations keyed by chunk index in a single JSON file per drive
- Environment variables for API keys — never commit secrets
- Use `package.json` for Node.js dependencies, no global installs assumed except ffmpeg

## Commands

```bash
# Install dependencies
npm install

# Parse GoPro file
node pipeline/parse-gopro.js <input.mp4>

# Run analysis pipeline
node pipeline/analyze.js <input.mp4>

# Start frontend dev server
npm run dev
```

## Progress Tracking

- Check `tasks.json` for current implementation status
- Check `SPEC.json` for the full implementation checklist
