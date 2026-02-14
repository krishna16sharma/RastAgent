"""
GPS interpolation module — maps any timestamp to (lat, lng)
using linear interpolation on a GPS track.
"""

import bisect
from typing import List, Dict, Optional, Tuple


class GPSInterpolator:
    """
    Interpolates GPS coordinates from a track of timestamped samples.

    Expects samples sorted by timestamp (cts in milliseconds).
    """

    def __init__(self, gps_samples: List[Dict]):
        """
        Args:
            gps_samples: List of GPS samples from GoPro parser.
                Each must have: lat, lon (or lng), cts (ms timestamp).
        """
        # Normalize and sort by cts
        self.samples = sorted(gps_samples, key=lambda s: s["cts"])
        self.timestamps = [s["cts"] for s in self.samples]

        if not self.samples:
            raise ValueError("GPS track is empty")

    @property
    def start_time(self) -> float:
        """First timestamp in ms."""
        return self.timestamps[0]

    @property
    def end_time(self) -> float:
        """Last timestamp in ms."""
        return self.timestamps[-1]

    @property
    def duration_sec(self) -> float:
        """Track duration in seconds."""
        return (self.end_time - self.start_time) / 1000.0

    def interpolate(self, timestamp_ms: float) -> Optional[Dict]:
        """
        Get interpolated GPS position at a given timestamp.

        Args:
            timestamp_ms: Timestamp in milliseconds (cts scale).

        Returns:
            Dict with lat, lng, alt (if available), or None if
            timestamp is outside the track range.
        """
        if not self.samples:
            return None

        # Clamp to track bounds
        if timestamp_ms <= self.timestamps[0]:
            s = self.samples[0]
            return self._to_point(s)

        if timestamp_ms >= self.timestamps[-1]:
            s = self.samples[-1]
            return self._to_point(s)

        # Find surrounding samples
        idx = bisect.bisect_right(self.timestamps, timestamp_ms) - 1
        s0 = self.samples[idx]
        s1 = self.samples[idx + 1]

        # Linear interpolation factor
        t0 = s0["cts"]
        t1 = s1["cts"]
        if t1 == t0:
            return self._to_point(s0)

        f = (timestamp_ms - t0) / (t1 - t0)

        lat = s0["lat"] + f * (s1["lat"] - s0["lat"])
        lon0 = self._get_lon(s0)
        lon1 = self._get_lon(s1)
        lng = lon0 + f * (lon1 - lon0)

        result = {"lat": lat, "lng": lng}

        # Interpolate altitude if available
        if "alt" in s0 and "alt" in s1:
            result["alt"] = s0["alt"] + f * (s1["alt"] - s0["alt"])

        return result

    def interpolate_sec(self, timestamp_sec: float) -> Optional[Dict]:
        """
        Interpolate using seconds relative to track start.

        Args:
            timestamp_sec: Seconds from the start of the GPS track.

        Returns:
            Dict with lat, lng (and alt if available).
        """
        timestamp_ms = self.start_time + (timestamp_sec * 1000.0)
        return self.interpolate(timestamp_ms)

    def interpolate_absolute_sec(self, abs_sec: float) -> Optional[Dict]:
        """
        Interpolate using absolute seconds from video start.

        This assumes GPS track cts=0 aligns with video start.

        Args:
            abs_sec: Absolute seconds from video start.

        Returns:
            Dict with lat, lng.
        """
        return self.interpolate(abs_sec * 1000.0)

    def _get_lon(self, sample: Dict) -> float:
        """Get longitude from sample (handles both 'lon' and 'lng' keys)."""
        return sample.get("lng", sample.get("lon", 0.0))

    def _to_point(self, sample: Dict) -> Dict:
        """Convert a GPS sample to a simple point dict."""
        result = {
            "lat": sample["lat"],
            "lng": self._get_lon(sample),
        }
        if "alt" in sample:
            result["alt"] = sample["alt"]
        return result

    def get_track_as_trace(self) -> List[Dict]:
        """
        Return the full GPS track in RouteMatcher trace format.

        Returns:
            List of dicts with lat, lng, timestamp.
        """
        return [
            {
                "lat": s["lat"],
                "lng": self._get_lon(s),
                "timestamp": s["cts"],
            }
            for s in self.samples
        ]
