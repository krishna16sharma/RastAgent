# RoadSense — End-to-End Code Walkthrough & Judge Q&A Prep

---

## Part 1: End-to-End Code Walkthrough

### The Big Picture

```
GoPro MP4 (video + embedded GPS)
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│  STEP 1: GPS Extraction                                  │
│  utils/gopro-parser.js → rast_agent/gopro/parser.py      │
│  Node.js parses GPMF binary telemetry from MP4           │
│  Output: [{lat, lon, alt, speed2d, cts, fix}, ...]       │
└──────────────────────────┬───────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────┐
│  STEP 2: Video Chunking                                  │
│  rast_agent/gopro/chunker.py                             │
│  ffmpeg stream-copy into 20s segments, 3s overlap        │
│  Output: chunk_000.mp4, chunk_001.mp4, ... + manifest    │
└──────────────────────────┬───────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────┐
│  STEP 3: Gemini Multimodal Analysis (parallel, 10 workers)│
│  rast_agent/analysis/gemini_client.py                    │
│  Upload chunk → Gemini 3 Pro (JSON mode) → hazard JSON │
│  Output per chunk: [{category, severity, bbox, action}]  │
└──────────────────────────┬───────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────┐
│  STEP 4: GPS Coordinate Mapping                          │
│  rast_agent/analysis/gps_mapper.py                       │
│  rast_agent/gopro/gps_interpolator.py                    │
│  timestamp_offset_sec → linear interpolation → lat/lng   │
│  Output: hazards now have GPS coordinates                │
└──────────────────────────┬───────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────┐
│  STEP 5: Deduplication                                   │
│  rast_agent/analysis/deduplicator.py                     │
│  Same category + within 100m (Haversine) → merge         │
│  Keep higher severity/confidence                         │
│  Output: unique hazard list with clean IDs               │
└──────────────────────────┬───────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────┐
│  STEP 6: Route Summary                                   │
│  rast_agent/analysis/gemini_client.py                    │
│  Second Gemini call on aggregated hazards                │
│  Output: quality_score (1-10), briefing, worst segment   │
└──────────────────────────┬───────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────┐
│  STEP 7: Cache & Serve                                   │
│  server.py (Flask)                                       │
│  Results → cache/{video}_results.json → REST API         │
│  /api/reports, /api/report/<file>, /api/video/<file>     │
└──────────────────────────┬───────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────┐
│  STEP 8: Frontend Visualization                          │
│  frontend/static/js/app.js + frontend/templates/index.html│
│  Split-screen: annotated video | Google Maps | summary   │
│  + Web Speech API voice alerts                           │
└──────────────────────────────────────────────────────────┘
```

---

### Module-by-Module Breakdown

#### 1. GPS Extraction — `utils/gopro-parser.js`

GoPro cameras embed GPMF (GoPro Metadata Format) telemetry directly inside MP4 files — GPS coordinates, accelerometer, gyroscope, all interleaved with video frames.

```
MP4 binary → gpmf-extract (parse GPMF track) → gopro-telemetry (decode GPS5 stream)
→ [{lat, lon, alt, speed2d, speed3d, date, cts, fix, precision}, ...]
```

- **`cts`** = millisecond timestamp relative to video start. This is how we sync GPS to video.
- **`fix`** = GPS fix quality (0=none, 2=2D, 3=3D). We filter for `fix >= 3` for accuracy.
- **`chunkVideo()`** splits the source MP4 using ffmpeg `-c copy` (stream-copy, no re-encoding = fast).

The Python wrapper (`rast_agent/gopro/parser.py`) calls this via subprocess — Node.js handles the binary parsing, Python orchestrates everything else.

#### 2. Video Chunking — `rast_agent/gopro/chunker.py`

Why chunk? Gemini has input limits, and 15-30 second segments are the sweet spot for detecting localized hazards. Too short = no context. Too long = token bloat and diluted attention.

```python
chunk_video(input_path, output_dir, chunk_duration=20, overlap=3)
```

- **3-second overlap** ensures hazards at chunk boundaries aren't missed. A pothole at second 19.5 appears in both chunk N and chunk N+1 — deduplication handles the double-count later.
- Outputs a `chunks_manifest.json` with start/end times per chunk.

#### 3. Gemini Analysis — `rast_agent/analysis/gemini_client.py`

The core of the system. Each chunk gets:

1. **Uploaded** to Gemini Files API (`client.files.upload()`)
2. **Analyzed** with system prompt + chunk-specific prompt, in **JSON mode**
3. **Parsed** — Gemini returns a raw JSON array of hazard objects (or `[]` for clean road)
4. **Cleaned up** — uploaded file deleted after processing

**Prompt strategy** (3-layer, in `prompts/`):

| Prompt | File | Role |
|---|---|---|
| System | `system_prompt.md` | Identity, India expertise, conservative bias |
| Chunk analysis | `chunk_analysis_prompt.md` | Per-segment detection with structured JSON schema |
| Route summary | `route_summary_prompt.md` | Aggregated quality report |

**Key prompt design choices:**
- *"A shadow is not a pothole."* — Explicit false-positive suppression for Indian road textures.
- *India-specific vocabulary:* yellow/black speed breaker markings, divider cuts, auto-rickshaw patterns, festival processions.
- *Actionable output:* every hazard must include `driver_action` — transforms detection into guidance.

**Parallelization:** 10 concurrent workers via `ThreadPoolExecutor`. A 10-minute video (~30 chunks) analyzes in ~3-4 minutes instead of 30+ sequential.

#### 4. GPS Mapping — `rast_agent/analysis/gps_mapper.py` + `gps_interpolator.py`

Gemini returns `timestamp_offset_sec` per hazard (seconds from chunk start). We need to convert that to a GPS coordinate.

```
absolute_time = chunk_start_sec + timestamp_offset_sec
gps = interpolator.interpolate_sec(absolute_time)
```

The `GPSInterpolator` does linear interpolation between GPS samples using `bisect` for efficient lookups. GoPro GPS typically samples at 10-18 Hz, so interpolation between samples gives sub-meter accuracy.

#### 5. Deduplication — `rast_agent/analysis/deduplicator.py`

Because of the 3-second overlap, the same pothole can appear in two adjacent chunks. Dedup rules:

- **Same category** + **within 100 meters** (Haversine distance) = same hazard
- Keep the detection with **higher severity** and **higher confidence**
- Re-assign clean IDs: H001, H002, H003...

#### 6. Route Summary — `gemini_client.generate_route_summary()`

A second Gemini call takes all deduplicated hazards and produces:

```json
{
  "route_quality_score": 6,        // 1-10, 10 = pristine
  "total_hazards": 12,
  "hazard_breakdown": {"POTHOLE": 4, "SPEED_BREAKER": 5, ...},
  "severity_distribution": {"LOW": 3, "MODERATE": 5, "HIGH": 3, "SEVERE": 1},
  "worst_segment": {"description": "Near KR Puram junction", "reason": "Cluster of 3 potholes + road work"},
  "route_briefing": "Moderately rough route with frequent speed breakers..."
}
```

#### 7. Flask Server — `server.py`

Minimal REST API:

| Endpoint | Returns |
|---|---|
| `GET /` | SPA index.html |
| `GET /api/reports` | List of cached reports `[{name, file, total_hazards, quality_score}]` |
| `GET /api/report/<file>` | Full analysis JSON |
| `GET /api/video/<path>` | Video stream (chunks or full) |
| `GET /api/config` | Google Maps API key for frontend |

No database — everything reads from the `cache/` directory. For a POC, this is the right call.

#### 8. Frontend — `app.js` + `index.html`

**Split-screen SPA with three synchronized components:**

**Left panel — Annotated video:**
- HTML5 `<video>` element + overlaid `<canvas>`
- On every `timeupdate` event: find hazards within a 3-second window, draw color-coded bounding boxes using normalized coordinates (0.0–1.0 → canvas pixels)
- Advisory banner shows the `driver_action` text for the current hazard
- Toggle between raw and annotated view

**Right panel — Google Maps:**
- GPS track drawn as blue polyline
- Hazard circles: radius and color scale with severity (green → red)
- **Position marker** (arrow) syncs with video playback time — updates by finding the closest GPS sample to current video timestamp
- Upcoming hazards pulse, past hazards fade to 0.15 opacity

**Bottom — Summary card:**
- Quality score badge (color-coded: green ≥7, yellow ≥4, red <4)
- Severity distribution histogram
- Category breakdown tags
- Route briefing text
- Worst segment callout

**Voice alerts — Web Speech API:**
- 2 seconds before each hazard's timestamp: TTS reads the `driver_action`
- Duplicate suppression with a `Set` of already-spoken hazard IDs
- Rate 1.1x, volume 0.8 — clear but not jarring

**No build step.** Plain ES6 JavaScript, works in any modern browser.

---

### MCP Server — `rast_agent/mcp_server/server.py`

Exposes four tools via FastMCP (Model Context Protocol) for AI agent orchestration:

| Tool | What it does |
|---|---|
| `get_google_maps_route` | Fetch route polyline + turn-by-turn steps |
| `analyze_route_coverage` | Match GPS trace to route, annotate with instructions |
| `analyze_video` | Run the full pipeline end-to-end |
| `get_hazard_report` | Load cached results |

This means an AI agent (e.g., Claude with MCP) can autonomously plan a route, analyze dashcam footage, and retrieve hazard reports — no human in the loop.

---

## Part 2: Judge Q&A Prep

### Technical Questions

**Q: Why Gemini instead of a fine-tuned vision model like YOLO?**

> YOLO detects "object in road." Gemini detects "unmarked speed breaker with faded yellow paint near a school zone, approach at 20 kmph." The long tail of Indian road hazards is effectively infinite — waterlogged patches, festival processions, auto-rickshaws reversing into traffic, cows, exposed manholes after rain. A fine-tuned model needs labeled training data for each scenario. Gemini handles novel situations out of the box because it *reasons* about what it sees, not just pattern-matches.
>
> For production at scale, the answer is *both*: use Gemini to bootstrap labeled data, then distill into lightweight per-hazard models for edge inference.

**Q: How accurate is the detection? What's the false positive/negative rate?**

> We've tuned for **conservative detection** — we'd rather miss a minor hazard than cry wolf on a shadow. The prompt explicitly instructs Gemini that Indian roads are rough by default, and only genuinely hazardous conditions should be flagged.
>
> We don't have formal precision/recall numbers (that would require a labeled ground-truth dataset, which is a future step). What we can show is the demo — real Bangalore footage with detections that match what you see in the video.
>
> The confidence score per hazard (0.0–1.0) from Gemini gives us a knob to filter aggressively if needed.

**Q: Why post-drive analysis and not real-time?**

> Honest answer: Gemini API latency (~5-10s per chunk) doesn't support real-time inference at this point. We made a deliberate architectural choice to pre-process and cache results for a smooth demo.
>
> But the architecture is designed for real-time: chunking already produces streaming segments, GPS mapping is instantaneous, and the frontend already handles time-synced playback. The bottleneck is inference speed, and that's solvable with edge-deployed distilled models.

**Q: How does GPS mapping work? How accurate is the coordinate assignment?**

> GoPro embeds GPS at 10-18 Hz with `cts` timestamps synced to video frames. We extract the full GPS track, then for each hazard detection, we take the `timestamp_offset_sec` from Gemini, compute the absolute video timestamp, and linearly interpolate between the two nearest GPS samples.
>
> At 18 Hz GPS and typical driving speeds (30-40 km/h in Bangalore), the interpolation error is sub-meter. The 100m deduplication radius is intentionally generous to absorb GPS drift and Gemini timestamp estimation uncertainty.

**Q: Why 20-second chunks with 3-second overlap?**

> **20 seconds** is long enough for Gemini to understand road context (speed, lane position, surroundings) but short enough to stay within token budget and maintain attention on localized hazards.
>
> **3-second overlap** covers the edge case where a hazard appears in the last frames of one chunk and first frames of the next. At 40 km/h, 3 seconds = ~33 meters — enough to guarantee any hazard visible in one chunk's boundary also appears in the adjacent chunk. Deduplication then merges the double-count.

**Q: How does deduplication work?**

> Simple but effective: if two detections have the **same hazard category** and their GPS coordinates are **within 100 meters** (Haversine distance), they're considered the same hazard. We keep the one with higher severity and confidence.
>
> 100m is generous — it absorbs GPS jitter, timestamp estimation error from Gemini, and the physical size of large hazard zones (e.g., a road work stretch). In production, we'd tune this per category (tighter for potholes, wider for road work zones).

**Q: How does the MCP server work? What's the use case?**

> MCP (Model Context Protocol) lets AI agents call our tools programmatically. An agent like Claude can autonomously:
> 1. Plan a route (`get_google_maps_route`)
> 2. Analyze dashcam footage for that route (`analyze_video`)
> 3. Retrieve the hazard report (`get_hazard_report`)
>
> Use case: an AI driving assistant that not only gives you directions but also warns you about road conditions based on crowdsourced dashcam data — all without human intervention.

**Q: What's the bounding box format and why normalized coordinates?**

> Bounding boxes use `{x_min, y_min, x_max, y_max}` with values from 0.0 to 1.0, where (0,0) is top-left and (1,1) is bottom-right. This is **resolution-independent** — the same annotation works whether the video is 1080p, 4K, or scaled to a mobile screen. The frontend multiplies by canvas dimensions at render time.

---

### Product & Business Questions

**Q: How is this different from Waze?**

> Waze requires **active reporting** — a driver has to tap the screen and report a hazard while driving. Adoption is low, data is sparse, and it goes stale fast.
>
> RoadSense is **fully passive**. You mount a dashcam and drive. Every kilometer is automatically surveyed. No taps, no effort. That's not an incremental improvement — it's a fundamentally different data collection model that can scale to millions of kilometers per day without asking anyone to do anything.

**Q: Who would use this?**

> Three user segments:
> 1. **Individual drivers** — dashcam or phone-as-dashcam, get hazard warnings on familiar or unfamiliar routes
> 2. **Fleet operators** — cab companies, logistics providers. They already have vehicles on every road. Turn their fleet into road sensors, improve driver safety, reduce vehicle damage costs
> 3. **Municipal governments** — city-level road health dashboards, prioritize repairs based on data instead of complaints, verify that fixes actually happened

**Q: What's the business model?**

> - **B2C freemium**: Free basic analysis, premium for real-time alerts and detailed route reports
> - **B2B fleet**: Per-vehicle subscription for fleet operators (road quality monitoring + driver safety)
> - **B2G data licensing**: Aggregate anonymized road quality data sold to municipal corporations and road authorities for infrastructure planning
> - **Insurance**: Road quality data as an input to route-based insurance risk scoring

**Q: How do you scale to millions of users?**

> **Phase 1 (Now):** Gemini cloud analysis, post-drive. Works for thousands of users.
> **Phase 2:** Distill Gemini's knowledge into lightweight specialized models (one per hazard category). 10-50x cost reduction.
> **Phase 3:** On-device preprocessing — phone or dashcam runs a small model to filter footage, only uploads anomalies. 100x bandwidth reduction.
> **Phase 4:** Edge inference — quantized models run directly on dashcam hardware. Zero upload, true real-time, near-zero marginal cost.
>
> Cost trajectory: ~$5/drive today → <$0.10/km at scale.

**Q: What about privacy? You're recording people's dashcam footage.**

> Several layers:
> 1. **On-device processing** (future) eliminates the need to upload raw video entirely
> 2. **Structured output only** — once analyzed, we store hazard JSON, not video. The video can be deleted immediately after analysis.
> 3. **No PII in outputs** — Gemini extracts road conditions, not license plates or faces
> 4. **Anonymized aggregation** — crowdsourced map shows hazard zones, not individual driver routes
> 5. **User control** — drivers choose when to analyze and can delete their data

**Q: What about liability? If you say a road is safe and it's not?**

> RoadSense provides **advisory information**, not guarantees. Same legal framing as Waze or Google Maps traffic estimates — "based on available data, not a substitute for driver judgment." We show confidence scores and "last observed" timestamps so drivers can assess data freshness themselves.

---

### Gemini-Specific Questions

**Q: How are you using Gemini specifically? What capabilities are you leveraging?**

> Three Gemini capabilities in one pipeline:
> 1. **Multimodal video understanding** — Gemini watches dashcam footage and identifies hazards frame-by-frame with spatial awareness (bounding boxes)
> 2. **Contextual reasoning** — not just "there's a hole in the road" but "this is an unmarked speed breaker near a school zone, common in residential Bangalore, approach at 20 kmph"
> 3. **Structured JSON generation** — JSON mode ensures every response is machine-parseable, no regex extraction needed
>
> Plus a second inference pass for route-level summarization and quality scoring.

**Q: Why JSON mode instead of function calling?**

> JSON mode gives us direct control over the output schema without defining tool schemas. For a detection task where the output is a variable-length array of hazards (0 to many), JSON mode is more natural than function calling. We get a raw JSON array — `[]` for clean road, `[{...}, {...}]` for hazards — and parse it directly.

**Q: How do you handle Gemini hallucinations?**

> Three defenses:
> 1. **Conservative prompting** — explicit instruction to return `[]` rather than invent hazards. "When in doubt, do not report."
> 2. **Confidence scores** — Gemini self-reports confidence (0.0–1.0). We can filter low-confidence detections.
> 3. **Multi-observation validation** (future) — in the crowdsourced model, a hallucinated hazard reported by one vehicle but not confirmed by subsequent drivers gets automatically downgraded and removed.

**Q: What's the API cost?**

> | Metric | Estimate |
> |---|---|
> | Gemini video input | ~$0.50/min of video |
> | Typical 10-min drive | ~$5 total (30 chunks + 1 summary) |
> | Target at scale (distilled) | < $0.10/km |
>
> For the hackathon POC, we've pre-analyzed footage and cached results — demo costs are zero.

**Q: What model specifically?**

> Gemini 2.5 Pro with multimodal video input in JSON generation mode. We upload MP4 chunks via the Files API and generate structured responses with the system + analysis prompt.

---

### Demo-Specific Questions

**Q: Is this real-time or pre-recorded?**

> Pre-analyzed and cached — **by design**. This is a post-drive analysis POC. The video plays back with cached annotations synchronized to the footage. We're honest about this: the architecture supports streaming chunks for near-real-time, but the hackathon demo prioritizes reliability over live inference latency.

**Q: What's the demo footage?**

> Real GoPro dashcam footage from Bangalore roads. Real potholes, real speed breakers, real chaos. Nothing staged.

**Q: Can you run it on a new video right now?**

> Yes — `python -m rast_agent.analysis.pipeline <new_video.mp4>` will run the full pipeline. It takes ~3-4 minutes for a 10-minute video (parallel chunk analysis). We can demo the pipeline running if there's time, but the cached demo shows the end result more smoothly.

---

### Hardball / Skeptical Questions

**Q: This is just a wrapper around the Gemini API. What's the technical depth?**

> The Gemini call is one step in a six-step pipeline. We built:
> - Binary telemetry extraction from GoPro's proprietary GPMF format
> - GPS interpolation engine for timestamp-to-coordinate mapping
> - Chunk-overlap deduplication with Haversine distance
> - Parallel processing with resume and incremental caching
> - Synchronized multi-modal frontend (video + map + voice, all time-locked)
> - MCP server for AI agent orchestration
> - Prompt engineering tuned for Indian road context with conservative detection bias
>
> Gemini is the brain. Everything around it is the nervous system that makes it useful.

**Q: Google could build this in a week with Street View data.**

> Google has Street View imagery but it's **periodic** (driven once every few years in Indian cities). Road conditions change daily — a pothole appears after monsoon rain, gets patched, and re-appears next month.
>
> RoadSense's model is **continuous observation from everyday drivers**. That's the moat — freshness at scale, powered by vehicles that are already on the road.

**Q: 100-meter deduplication radius seems crude. What about dense urban areas?**

> Fair point. 100m works well for suburban/highway stretches. In dense urban areas (narrow lanes, closely spaced hazards), we'd tune this per-category: ~20m for potholes, ~50m for speed breakers, ~200m for road work zones. The architecture supports per-category thresholds — it's a configuration change, not a redesign.

**Q: What if the dashcam is dirty, obstructed, or poorly mounted?**

> Gemini's vision model is surprisingly robust to image quality issues — it handles rain-splattered windshields, glare, and partial obstructions better than purpose-built CV models. But for systematic quality issues (e.g., camera pointing at the dashboard), the confidence scores would be consistently low, and we'd flag the data source as unreliable. In production, a simple frame quality check before uploading would filter out unusable footage.

**Q: How do you handle night driving?**

> GoPro footage quality drops significantly at night, and Gemini's detection confidence drops with it. For the POC, we focus on daytime footage. In production, we'd add night-specific prompt tuning (headlight glare suppression, emphasis on reflective markers) and potentially fuse dashcam video with LiDAR/ultrasonic data from newer vehicles.

---

### Vision & Future Questions

**Q: What's the 5-year vision?**

> **Year 1:** Phone-as-dashcam app launch. Build initial hazard map from early adopters and fleet partnerships.
> **Year 2:** Fleet partnerships with cab/logistics companies. Millions of km/day. Temporal intelligence layer — hazards that decay and get reconfirmed.
> **Year 3:** "Smoothest route" option integrated into navigation. Municipal dashboards for road authorities.
> **Year 4:** Edge inference on dashcam hardware. True real-time alerts. Vehicle-specific routing.
> **Year 5:** Standard data layer for all navigation apps — the "road weather" that every mapping service subscribes to.

**Q: Why India first?**

> India is the **hardest problem** — chaotic roads, informal infrastructure, diverse hazard types, extreme conditions. If we solve India, every other market is easier.
>
> Plus: 300M+ registered vehicles, massive smartphone penetration, growing dashcam adoption, and a government that's actively investing in road safety (National Highway Authority, Smart Cities Mission). The market pull is real.

**Q: What's your competitive moat?**

> 1. **Data network effect** — more drivers → better map → more drivers. First-mover advantage in crowdsourced road quality data for India.
> 2. **Gemini-native architecture** — built from the ground up on multimodal AI, not retrofitted. As Gemini improves, we improve automatically.
> 3. **Prompt engineering IP** — India-specific detection prompts tuned through real-world testing. Not trivially replicable.
> 4. **MCP integration** — ready for the AI agent ecosystem. When every car has an AI copilot, they'll need our data.

---

## Part 3: Quick Reference Card (for on-stage)

### One-liner
> Google Maps tells you *where to go*. RoadSense tells you *what you'll face when you get there*.

### Key numbers
- 7 hazard categories, 5 severity levels
- 10-18 Hz GPS from GoPro telemetry
- 20-second chunks, 3-second overlap
- 10 parallel Gemini workers
- 100m deduplication radius (Haversine)
- ~3-4 minutes to analyze a 10-minute drive
- ~$5 per 10-minute analysis (Gemini cost)

### Tech stack in one breath
> GoPro GPMF extraction in Node.js, ffmpeg chunking, Gemini 2.5 Pro multimodal analysis in JSON mode, GPS interpolation, Haversine deduplication, Flask REST API, split-screen SPA with Google Maps and Web Speech API voice alerts, FastMCP server for AI agent integration.

### If you forget everything else, remember this
> **Passive detection vs. active reporting.** That's the insight. Every dashcam drive becomes a road survey without the driver doing anything. Scale that to fleet-level, and you have a living map of road conditions that no one has ever built.
