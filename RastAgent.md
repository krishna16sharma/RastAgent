# RoadSense: Road Hazard Intelligence for Indian Navigation

**Gemini 3 Bengaluru Hackathon — Project Design Doc v2**

---

## Problem Statement

Indian roads present navigation challenges that current mapping solutions don't capture: potholes, unmarked speed breakers, informal junctions, sudden diversions, and other hyper-local hazards. Existing navigation apps optimize for distance and traffic but are blind to road-level context that directly impacts safety and driving experience.

Critically, the current model for reporting road hazards (manual user reports on Google Maps or Waze) requires **active effort** — most drivers never bother. The result is a perpetually incomplete and stale picture of actual road conditions.

## Solution Overview

**RoadSense** combines dashcam footage with GPS data and Gemini 3 Pro's multimodal capabilities to **passively detect and annotate** real-world road hazards — zero driver effort required. The system processes post-drive footage and presents a split-screen interface: annotated dashcam feed alongside a Google Maps view with severity-coded hazard zones and actionable driver advisories.

The key insight is **passive, automatic detection** vs. active user reporting. Every dashcam-equipped drive becomes a road survey without the driver doing anything.

---

## Architecture (POC)

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  GoPro Footage   │────▶│  Gemini 3 Pro    │────▶│   Annotation Layer  │
│  (Video + GPS)   │     │  (Multimodal)    │     │   (Hazard Labels +  │
│                  │     │  Structured JSON  │     │    GPS Coordinates)  │
└─────────────────┘     │  + JSON Mode      │     └──────────┬──────────┘
                        └──────────────────┘                 │
                                                             ▼
                                                  ┌─────────────────────┐
                                                  │    Web UI (Split)    │
                                                  │  ┌───────┬────────┐ │
                                                  │  │Annotated│Google │ │
                                                  │  │ Video + │ Maps  │ │
                                                  │  │Advisory │Hazard │ │
                                                  │  │ Feed    │ Zones │ │
                                                  │  └───────┴────────┘ │
                                                  │  ┌──────────────┐   │
                                                  │  │Route Summary │   │
                                                  │  │    Card      │   │
                                                  │  └──────────────┘   │
                                                  └─────────────────────┘
```

### Data Flow

1. **Input** — GoPro dashcam footage with embedded GPS metadata (GPMF format)
2. **GPS Extraction** — Parse GPS track from GoPro telemetry into (lat, lng, timestamp) tuples
3. **Chunking** — Split video into 15–30 second segments with 2–3 second overlap to avoid missing hazards at boundaries
4. **Analysis** — Each chunk is sent to Gemini 3 Pro with a structured hazard detection prompt; responses returned as strict JSON (hazard type, severity, timestamp offset, bounding box, driver advisory)
5. **GPS Mapping** — Map each hazard's timestamp back to GPS coordinates via interpolation on the extracted GPS track
6. **Deduplication** — Merge overlapping detections from adjacent chunks using 100m proximity radius
7. **Route Summary** — Aggregate all hazards and generate a route quality report via a second Gemini call
8. **Display** — Web interface with synchronized annotated video, severity-coded hazard zones on Google Maps, and a route summary card

### POC Scope & Honest Framing

This is a **post-drive analysis** system for the POC. Video is pre-processed through Gemini before the demo, and the UI plays back cached annotations synchronized to the footage. The architecture supports near-real-time streaming chunks in production, but the hackathon demo prioritizes a smooth, reliable experience over live inference.

---

## Hazard Detection

### Categories

| Category | Code | Description |
|---|---|---|
| Potholes | `POTHOLE` | Visible road surface damage, craters, broken tarmac |
| Speed Breakers | `SPEED_BREAKER` | Marked or unmarked speed bumps, raised road surfaces |
| Informal Junctions | `INFORMAL_JUNCTION` | Unmarked merge points, illegal divider cuts, uncontrolled intersections |
| Pedestrian Zones | `PEDESTRIAN_ZONE` | Active crossings, school zones, market areas with foot traffic |
| Overhead Obstructions | `OVERHEAD_OBSTRUCTION` | Low-hanging branches, cables, signage intruding into vehicle clearance |
| Road Works | `ROAD_WORK` | Active construction, repair zones, exposed manholes, barricades |
| Sharp Curves | `SHARP_CURVE` | Blind turns, unexpectedly tight curves, hairpin bends |
| Surface Changes | `SURFACE_CHANGE` | Paved-to-unpaved transitions, gravel patches, waterlogged sections |
| Obstructions | `OBSTRUCTION` | Parked vehicles narrowing road, debris, animals, temporary barriers |

### Severity Scale

| Level | Label | Description |
|---|---|---|
| 1 | LOW | Minor inconvenience, no speed adjustment needed |
| 2 | MODERATE | Should reduce speed, mild discomfort if ignored |
| 3 | HIGH | Must slow down significantly, potential vehicle damage |
| 4 | SEVERE | Dangerous if not addressed, requires near-stop or lane change |
| 5 | CRITICAL | Road effectively impassable or extremely dangerous |

### Annotation Output (per hazard)

```json
{
  "hazard_id": "H001",
  "category": "POTHOLE",
  "severity": 3,
  "timestamp_offset_sec": 4.2,
  "description": "Large pothole spanning left half of lane, ~1m diameter, partially water-filled",
  "bounding_box": {
    "x_min": 0.2, "y_min": 0.6,
    "x_max": 0.5, "y_max": 0.8
  },
  "driver_action": "Reduce speed and steer right to avoid",
  "confidence": 0.85
}
```

**Design notes:**
- Bounding boxes use normalized coordinates (0.0–1.0) for resolution independence
- `driver_action` field turns detection into actionable advisory — the key differentiator
- Conservative detection bias: Indian roads are rough by default; only genuinely hazardous conditions are flagged

---

## POC Demo

### Format

Split-screen web application with three components:

- **Left panel** — GoPro footage with real-time annotation overlays (bounding boxes, hazard labels, and driver advisories generated by Gemini)
- **Right panel** — Google Maps showing the driven route with **severity-coded hazard zones** (100m radius circles, color-graded green → red) at corresponding GPS coordinates
- **Bottom card** — Route summary with total hazard count, quality score, worst segment, and natural language route briefing
- **Audio alerts** — Voice advisories ("Pothole ahead — steer right") via Web Speech API as each hazard approaches in the video playback

### Synchronization

As the video progresses, the map tracks the current position and highlights upcoming hazard zones. Past hazards fade, upcoming hazards pulse — creating a sense of forward awareness.

### Demo Flow

1. Show a raw GoPro clip of a Bangalore route — no annotations, just the chaotic road
2. Show the same route through RoadSense — annotated video, hazard zones, voice alerts
3. End with the route summary card — "This 4km route has 12 hazards, road quality 5/10, worst segment near KR Puram junction"

The before/after contrast makes the value proposition instantly obvious.

### Key Technical Steps

1. Extract GPS track from GoPro metadata (GPMF/GPX format)
2. Chunk video into 15–30 second segments with 2–3 second overlap
3. Send each chunk to Gemini 3 Pro with structured hazard detection prompt; use JSON mode for reliable parsing
4. Parse and deduplicate annotations across chunks (100m GPS proximity)
5. Run route summary prompt on aggregated hazards
6. Cache all responses as JSON keyed by chunk index
7. Render split-screen UI: Google Maps JavaScript API + synchronized HTML5 video player + Web Speech API for voice alerts
8. UI reads from cache during demo — smooth playback, honest architecture

---

## Prompt Strategy

Three-layer prompt design:

| Prompt | Purpose | When |
|---|---|---|
| **System Prompt** | Establishes RoadSense identity, Indian road expertise | Set once per session |
| **Chunk Analysis Prompt** | Per-segment hazard detection with structured JSON output | Per video chunk |
| **Route Summary Prompt** | Aggregated drive report with quality score and narrative | Once, post-processing |

**Critical prompt design decisions:**
- **Conservative detection bias** — Explicit instruction to avoid false positives from shadows, normal road texture, and parked vehicles. "A shadow is not a pothole."
- **India-specific context** — Prompt tuned for Indian road conventions: yellow/black speed breaker markings, divider cuts, festival processions, auto-rickshaw behavior
- **Structured JSON output** — Gemini JSON mode for reliable parsing, no free-text extraction
- **Driver advisory generation** — Each hazard includes a recommended action, transforming detection into guidance

Full prompt specifications: `RoadSense_Gemini_Prompt.md`

---

## Tech Stack

| Component | Technology |
|---|---|
| Video Analysis | Gemini 3 Pro (multimodal, JSON mode) |
| GPS Extraction | GoPro GPMF / GPX telemetry parser |
| Map Display | Google Maps JavaScript API |
| Voice Alerts | Web Speech API (TTS) |
| Frontend | HTML/JS or React (single-page app) |
| Data Format | JSON (cached annotations + route summary) |
| Hosting | Local demo deployment |

---

## Cost & Scalability (Judge Q&A Prep)

### Why Gemini over a fine-tuned vision model (YOLO, etc.)?

A fine-tuned model detects potholes. Gemini detects "there's a festival procession blocking the left lane and an auto-rickshaw is reversing into oncoming traffic." The long tail of Indian road hazards is effectively infinite — Gemini handles novel situations without retraining. For a POC, this flexibility is the entire point.

### API Cost Estimate

| Metric | Estimate |
|---|---|
| Gemini 3 Pro video input | ~$0.50 per minute of video |
| 10-minute drive | ~$5 total |
| Target at scale (distilled models) | < $0.10 per km |

### Scalability Path

- **On-device preprocessing** — Lightweight models on the dashcam or phone filter footage, transmitting only relevant event clips (not raw video)
- **Compact transmission** — Compress visual context for efficient upload, reducing bandwidth
- **Task-specific distillation** — Distill Gemini's general capabilities into specialized per-hazard models, reducing cloud inference cost by 10–50x
- **Edge inference** — Deploy quantized hazard detection models directly on dashcam hardware for true real-time operation

---

## Future Vision

### Collective Road Intelligence

The long-term vision extends beyond a single dashcam to a **collective consciousness** of road conditions:

- **Crowdsourced hazard map** — Multiple dashcam-equipped vehicles continuously contribute observations, building a living map of road conditions across Indian cities
- **Temporal belief system** — Hazard reports decay over time and get reinforced or invalidated by newer observations. A pothole reported 3 months ago but not confirmed by recent drivers gets downgraded; one confirmed by multiple recent drives gets high confidence
- **Freshness signals** — Newer observations at overlapping coordinates override older ones, keeping the map current and trustworthy
- **Route scoring** — Before a driver starts a trip, show a road quality score for each route option. Not just "fastest" or "shortest" but "smoothest"

### Extended Hazard Coverage

Beyond POC categories: road flooding, road collapses, temporary blockages (events/festivals), signaling confusion, night-specific risks, habitual jaywalking zones, seasonal hazards, and construction zone progression tracking.

---

## Why This Wins

| Dimension | Strength |
|---|---|
| **India-specific** | Addresses real, daily pain points that global navigation products ignore |
| **Multimodal showcase** | Demonstrates Gemini 3 Pro's vision + reasoning on a practical, tangible problem |
| **Zero-effort data collection** | Passive detection vs. active reporting — fundamentally different from existing solutions |
| **Clear demo impact** | Before/after comparison, voice alerts, and route summary make value instantly visible |
| **Honest architecture** | Post-drive analysis POC with a credible path to real-time at scale |
| **Scalable vision** | Single dashcam today → collective road intelligence tomorrow |
