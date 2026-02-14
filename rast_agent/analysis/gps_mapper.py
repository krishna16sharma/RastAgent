"""
GPS coordinate mapper — maps hazard timestamps to GPS coordinates.

Takes hazard detections (with timestamp offsets relative to chunk start)
and maps them to absolute GPS coordinates using the GPS interpolator.
"""

from typing import List, Dict
from rast_agent.gopro.gps_interpolator import GPSInterpolator


def map_hazards_to_gps(
    hazards: List[Dict],
    chunk_start_sec: float,
    interpolator: GPSInterpolator,
) -> List[Dict]:
    """
    Map hazard timestamps to GPS coordinates.

    Each hazard has a timestamp_offset_sec relative to its chunk start.
    This converts it to an absolute timestamp and interpolates GPS.

    Args:
        hazards: List of hazard dicts from Gemini analysis.
            Each must have timestamp_offset_sec (float).
        chunk_start_sec: The start time of this chunk in the full video.
        interpolator: GPSInterpolator initialized with the drive's GPS track.

    Returns:
        Hazards with added fields:
        - gps: { lat, lng } interpolated coordinates
        - timestamp_sec: absolute timestamp in the drive
    """
    mapped = []

    for hazard in hazards:
        h = dict(hazard)
        offset = h.get("timestamp_offset_sec", 0.0)
        abs_sec = chunk_start_sec + offset
        h["timestamp_sec"] = abs_sec

        # Interpolate GPS position at this timestamp
        gps = interpolator.interpolate_absolute_sec(abs_sec)
        if gps:
            h["gps"] = {"lat": gps["lat"], "lng": gps["lng"]}
        else:
            h["gps"] = None

        mapped.append(h)

    return mapped
