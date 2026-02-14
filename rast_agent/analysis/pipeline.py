"""
Analysis orchestrator pipeline — end-to-end processing of a GoPro drive.

Steps:
1. Extract GPS from GoPro MP4
2. Chunk video into segments
3. Send each chunk to Gemini for hazard analysis
4. Map hazards to GPS coordinates
5. Deduplicate overlapping detections
6. Generate route summary
7. Write results to cache
"""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Optional

from rast_agent.gopro.parser import extract_gps
from rast_agent.gopro.chunker import chunk_video
from rast_agent.gopro.gps_interpolator import GPSInterpolator
from rast_agent.analysis.gemini_client import analyze_chunk, generate_route_summary
from rast_agent.analysis.gps_mapper import map_hazards_to_gps
from rast_agent.analysis.deduplicator import deduplicate_hazards


# Default cache directory
_CACHE_DIR = Path(__file__).resolve().parents[2] / "cache"


def run_pipeline(
    video_path: str,
    output_dir: Optional[str] = None,
    cache_dir: Optional[str] = None,
    chunk_duration: int = 20,
    chunk_overlap: int = 3,
    model_name: str = "gemini-3-pro-preview",
    skip_existing: bool = True,
    max_workers: int = 10,
) -> Dict:
    """
    Run the full analysis pipeline on a GoPro video.

    Args:
        video_path: Path to the GoPro MP4 file.
        output_dir: Directory for video chunks. Defaults to cache/chunks/.
        cache_dir: Directory for cached results. Defaults to cache/.
        chunk_duration: Chunk duration in seconds.
        chunk_overlap: Overlap between chunks in seconds.
        model_name: Gemini model name.
        skip_existing: Skip analysis if cache file already exists.
        max_workers: Max parallel chunk analyses (default 10).

    Returns:
        Dict with keys:
        - hazards: deduplicated list of hazard dicts
        - summary: route summary dict
        - chunks: chunk manifest
        - gps_track: raw GPS samples
        - cache_path: path to the cached results file
    """
    video_path = os.path.abspath(video_path)
    video_name = Path(video_path).stem

    # Set up directories
    cache_dir = Path(cache_dir) if cache_dir else _CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)

    output_dir = output_dir or str(cache_dir / "chunks" / video_name)
    cache_file = cache_dir / f"{video_name}_results.json"

    # Check for existing cache
    if skip_existing and cache_file.exists():
        print(f"Loading cached results from {cache_file}")
        with open(cache_file) as f:
            return json.load(f)

    print(f"Processing: {video_path}")

    # Step 1: Extract GPS
    print("Step 1/6: Extracting GPS telemetry...")
    gps_samples = extract_gps(video_path)
    print(f"  Found {len(gps_samples)} GPS samples")

    if not gps_samples:
        print("  WARNING: No GPS data found. Hazards will not have coordinates.")
        interpolator = None
    else:
        interpolator = GPSInterpolator(gps_samples)
        print(f"  Track duration: {interpolator.duration_sec:.1f}s")

    # Step 2: Chunk video
    print("Step 2/6: Chunking video...")
    chunks = chunk_video(video_path, output_dir, chunk_duration, chunk_overlap)
    print(f"  Created {len(chunks)} chunks")

    # Step 3 & 4: Analyze each chunk + map GPS (parallel)
    print(f"Step 3/6: Analyzing {len(chunks)} chunks with Gemini ({max_workers} workers)...")
    all_hazards = []
    chunk_results = {}

    def _process_chunk(chunk):
        """Analyze a single chunk and map GPS coordinates."""
        idx = chunk["chunk_index"]
        t0 = time.time()
        print(f"  [chunk {idx:03d}] START uploading + analyzing ({chunk['start_sec']:.1f}s - {chunk['end_sec']:.1f}s)...")

        try:
            hazards = analyze_chunk(
                chunk["file_path"],
                idx,
                chunk["start_sec"],
                chunk["end_sec"],
                model_name=model_name,
            )
        except Exception as e:
            print(f"  [chunk {idx:03d}] ERROR after {time.time() - t0:.1f}s: {e}")
            hazards = []

        elapsed = time.time() - t0
        print(f"  [chunk {idx:03d}] DONE in {elapsed:.1f}s — {len(hazards)} hazards found")
        for h in hazards:
            print(f"    - {h.get('category', '?')} sev={h.get('severity', '?')}: {h.get('description', '')[:80]}")

        # Map to GPS if interpolator available
        if interpolator and hazards:
            hazards = map_hazards_to_gps(hazards, chunk["start_sec"], interpolator)

        return idx, hazards

    pipeline_t0 = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process_chunk, chunk): chunk for chunk in chunks}

        for future in as_completed(futures):
            idx, hazards = future.result()
            chunk_results[idx] = hazards
            all_hazards.extend(hazards)

    print(f"  All chunks analyzed in {time.time() - pipeline_t0:.1f}s")

    print(f"  Total raw hazards: {len(all_hazards)}")

    # Step 5: Deduplicate
    print("Step 4/6: Deduplicating hazards...")
    deduped = deduplicate_hazards(all_hazards)
    print(f"  After dedup: {len(deduped)} unique hazards")

    # Step 6: Route summary
    print("Step 5/6: Generating route summary...")
    try:
        summary = generate_route_summary(deduped, model_name=model_name)
    except Exception as e:
        print(f"  ERROR generating summary: {e}")
        summary = {
            "route_quality_score": 0,
            "total_hazards": len(deduped),
            "hazard_breakdown": {},
            "severity_distribution": {},
            "worst_segment": {},
            "route_briefing": "Summary generation failed.",
        }

    # Step 7: Cache results
    print("Step 6/6: Caching results...")
    results = {
        "video": video_path,
        "gps_track": gps_samples,
        "chunks": chunks,
        "chunk_results": {str(k): v for k, v in chunk_results.items()},
        "hazards": deduped,
        "summary": summary,
        "cache_path": str(cache_file),
    }

    with open(cache_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"Results cached to {cache_file}")
    print(f"Done! {len(deduped)} hazards detected, quality score: {summary.get('route_quality_score', 'N/A')}")

    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <gopro_video.mp4> [chunk_sec] [overlap_sec]")
        sys.exit(1)

    video = sys.argv[1]
    dur = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    ovl = int(sys.argv[3]) if len(sys.argv) > 3 else 3

    results = run_pipeline(video, chunk_duration=dur, chunk_overlap=ovl, skip_existing=False)
    print(json.dumps(results["summary"], indent=2))
