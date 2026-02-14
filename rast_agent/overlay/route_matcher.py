import googlemaps
from typing import List, Dict, Optional, Tuple
import math

class RouteMatcher:
    def __init__(self, route_data: Dict):
        """
        Initialize with a route object from Google Maps API.
        """
        self.route_data = route_data
        self.polyline_points = self._decode_polyline()
        self.segments = self._parse_steps()

    def _decode_polyline(self) -> List[Tuple[float, float]]:
        """
        Decodes the overview polyline into a list of (lat, lng).
        """
        encoded = self.route_data.get("overview_polyline")
        if not encoded:
            return []
        return googlemaps.convert.decode_polyline(encoded)

    def _parse_steps(self) -> List[Dict]:
        """
        Parses route steps for easier lookup.
        Each segment will have a start_index and end_index relative to the full polyline?
        Actually, the 'steps' in the API response have their own polylines.
        """
        return self.route_data.get("steps", [])

    def find_nearest_point(self, lat: float, lng: float) -> Optional[Dict]:
        """
        Finds the nearest point on the route to the given coordinates.
        Returns context about that point (e.g., "Step 3: Turn Left").
        """
        if not self.polyline_points:
            return None

        min_dist = float('inf')
        nearest_idx = -1

        for i, point in enumerate(self.polyline_points):
            # Euclidean distance is rough but likely sufficient for "nearest point on line" 
            # at this scale. For production, use Haversine.
            # point is {'lat': x, 'lng': y} from googlemaps decoder
            d = (point['lat'] - lat)**2 + (point['lng'] - lng)**2
            if d < min_dist:
                min_dist = d
                nearest_idx = i

        if nearest_idx == -1:
            return None
            
        # Now map 'nearest_idx' to a specific Instruction Step
        # This is tricky because 'steps' has its own polyline.
        # Simple heuristic: Just return the raw point for now.
        # TODO: Map index to Step Instruction
        
        return {
            "lat": self.polyline_points[nearest_idx]['lat'],
            "lng": self.polyline_points[nearest_idx]['lng'],
            "index": nearest_idx,
            "total_points": len(self.polyline_points)
        }

    def get_instruction_for_point(self, lat: float, lng: float) -> str:
        """
        Returns the navigation instruction relevant to this location.
        """
        # 1. Find nearest point on the master polyline
        match = self.find_nearest_point(lat, lng)
        if not match:
            return "Off route"
            
        # 2. Iterate through steps to see which step covers this point.
        # Limitation: The 'overview_polyline' is simplified. 
        # The 'steps' have detailed polylines. 
        # A robust matcher would verify against step polylines.
        
        # For MVP, let's just search all steps.
        best_step = None
        min_step_dist = float('inf')
        
        for step in self.segments:
            step_poly = step.get('polyline') # encoded string
            if step_poly:
                decoded = googlemaps.convert.decode_polyline(step_poly)
                # Check distance to this step's path
                for pt in decoded:
                     d = (pt['lat'] - lat)**2 + (pt['lng'] - lng)**2
                     if d < min_step_dist:
                         min_step_dist = d
                         best_step = step

        if best_step and min_step_dist < 0.0001: # Threshold (approx 10-20m)
             # Strip HTML tags from instruction
             import re
             raw_instr = best_step.get('instruction', '')
             clean_instr = re.sub('<[^<]+?>', '', raw_instr)
             return clean_instr
             
        return "Proceed along route"
