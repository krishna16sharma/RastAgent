
export interface BoundingBox {
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
}

export interface HazardDetection {
  hazard_id: string;
  category: 'POTHOLE' | 'SPEED_BREAKER' | 'PEDESTRIAN_ZONE' | 'OVERHEAD_OBSTRUCTION' | 'ROAD_WORK' | 'SHARP_CURVE' | 'SURFACE_CHANGE';
  severity: number; // 1 to 5
  timestamp_offset_sec: number;
  description: string;
  bounding_box: BoundingBox;
  driver_action: string;
  confidence: number;
}
