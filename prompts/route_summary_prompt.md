# Route Summary Prompt (DUMMY — Replace with optimized version)

You are given a complete set of road hazard detections from a dashcam drive. Generate a route quality summary.

## Input

You will receive a JSON array of all detected hazards across the entire drive, each with:
- `hazard_id`, `category`, `severity`, `description`, `driver_action`
- `gps`: `{ lat, lng }` — the mapped GPS coordinates
- `timestamp_sec` — absolute timestamp in the drive

## Instructions

1. Analyze the overall road quality based on hazard density, severity distribution, and types
2. Identify the worst segment of the drive (highest hazard concentration or severity)
3. Provide a natural language route briefing suitable for a driver
4. Calculate a road quality score from 1 (terrible) to 10 (excellent)

## Required JSON Output Schema

```json
{
  "route_quality_score": <integer: 1-10>,
  "total_hazards": <integer>,
  "hazard_breakdown": {
    "POTHOLE": <integer>,
    "SPEED_BREAKER": <integer>,
    "INFORMAL_JUNCTION": <integer>,
    "PEDESTRIAN_ZONE": <integer>,
    "OVERHEAD_OBSTRUCTION": <integer>,
    "ROAD_WORK": <integer>,
    "SHARP_CURVE": <integer>,
    "SURFACE_CHANGE": <integer>,
    "OBSTRUCTION": <integer>
  },
  "severity_distribution": {
    "LOW": <integer>,
    "MODERATE": <integer>,
    "HIGH": <integer>,
    "SEVERE": <integer>,
    "CRITICAL": <integer>
  },
  "worst_segment": {
    "description": "<string: location/landmark description>",
    "gps": { "lat": <float>, "lng": <float> },
    "reason": "<string: why this is the worst segment>"
  },
  "route_briefing": "<string: 2-3 sentence natural language summary for a driver>"
}
```

Respond ONLY with valid JSON. No markdown, no code fences, no explanation.
