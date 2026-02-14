"""
Hazard deduplication — merges overlapping detections from
adjacent video chunks using GPS proximity and category matching.
"""

import math
from typing import List, Dict


def haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate the distance in meters between two GPS coordinates."""
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def deduplicate_hazards(
    hazards: List[Dict],
    proximity_meters: float = 100.0,
) -> List[Dict]:
    """
    Merge duplicate hazard detections from overlapping video chunks.

    Two hazards are considered duplicates if:
    1. They have the same category
    2. Their GPS coordinates are within proximity_meters

    When merging, the detection with higher severity is kept.
    Descriptions are merged if they differ.

    Args:
        hazards: List of hazard dicts, each must have:
            - category: str
            - severity: int
            - gps: dict with lat, lng
            - Plus any other fields (description, driver_action, etc.)
        proximity_meters: Maximum distance to consider as duplicate.

    Returns:
        Deduplicated list of hazards.
    """
    if not hazards:
        return []

    merged = []

    for hazard in hazards:
        gps = hazard.get("gps")
        if not gps:
            merged.append(hazard)
            continue

        # Check if this hazard matches an existing merged one
        found_match = False
        for existing in merged:
            existing_gps = existing.get("gps")
            if not existing_gps:
                continue

            # Same category check
            if existing["category"] != hazard["category"]:
                continue

            # Proximity check
            dist = haversine_meters(
                gps["lat"], gps["lng"],
                existing_gps["lat"], existing_gps["lng"],
            )

            if dist <= proximity_meters:
                # Merge: keep higher severity
                if hazard.get("severity", 0) > existing.get("severity", 0):
                    existing["severity"] = hazard["severity"]
                    existing["description"] = hazard.get("description", existing.get("description"))
                    existing["driver_action"] = hazard.get("driver_action", existing.get("driver_action"))
                    existing["bounding_box"] = hazard.get("bounding_box", existing.get("bounding_box"))

                # Keep higher confidence
                if hazard.get("confidence", 0) > existing.get("confidence", 0):
                    existing["confidence"] = hazard["confidence"]

                found_match = True
                break

        if not found_match:
            merged.append(dict(hazard))

    # Re-assign hazard IDs
    for i, h in enumerate(merged):
        h["hazard_id"] = f"H{i + 1:03d}"

    return merged
