#!/usr/bin/env python3
"""
Run Gemini hazard analysis on pre-chunked video.

Usage:
    # Analyze all 44 chunks (full run)
    python run_analysis.py

    # Analyze only first 5 chunks (test run)
    python run_analysis.py --limit 5

    # Resume from a partially completed run (skips already-analyzed chunks)
    python run_analysis.py --resume

    # Use a different model
    python run_analysis.py --model gemini-2.5-pro-preview-06-05

    # Adjust parallelism (default: 3 to be gentle on API)
    python run_analysis.py --workers 5
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent
CACHE_DIR = PROJECT_ROOT / "cache"
MANIFEST_PATH = CACHE_DIR / "chunks" / "output_compressed" / "chunks_manifest.json"
RESULTS_PATH = CACHE_DIR / "output_compressed_results.json"

# Ensure rast_agent is importable
sys.path.insert(0, str(PROJECT_ROOT))

from rast_agent.analysis.gemini_client import analyze_chunk, generate_route_summary
from rast_agent.analysis.deduplicator import deduplicate_hazards


def load_manifest() -> list:
    """Load the pre-generated chunks manifest."""
    if not MANIFEST_PATH.exists():
        print(f"ERROR: Manifest not found at {MANIFEST_PATH}")
        print("Run the chunking step first.")
        sys.exit(1)

    with open(MANIFEST_PATH) as f:
        data = json.load(f)
    return data["chunks"]


def load_partial_results() -> dict:
    """Load partially completed results for resume support."""
    if RESULTS_PATH.exists():
        with open(RESULTS_PATH) as f:
            return json.load(f)
    return {}


def save_results(chunk_results: dict, all_hazards: list, summary: dict | None = None):
    """Save current results to disk (supports incremental saves)."""
    results = {
        "video": "output_compressed.mp4",
        "video_filename": "output_compressed.mp4",
        "gps_track": [],  # No GPS for non-GoPro footage
        "chunk_results": {str(k): v for k, v in chunk_results.items()},
        "hazards": all_hazards,
        "summary": summary or {
            "route_quality_score": 0,
            "total_hazards": len(all_hazards),
            "route_briefing": "Analysis in progress...",
        },
        "cache_path": str(RESULTS_PATH),
    }
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2, default=str)


def process_chunk(chunk: dict, model_name: str) -> tuple:
    """Analyze a single chunk. Returns (chunk_index, hazards_list)."""
    idx = chunk["chunk_index"]
    t0 = time.time()
    print(f"  [{idx:03d}/044] Analyzing {chunk['start_sec']:.0f}s–{chunk['end_sec']:.0f}s ...")

    try:
        hazards = analyze_chunk(
            chunk["file_path"],
            idx,
            chunk["start_sec"],
            chunk["end_sec"],
            model_name=model_name,
        )
    except Exception as e:
        print(f"  [{idx:03d}] ERROR: {e}")
        hazards = []

    elapsed = time.time() - t0
    print(f"  [{idx:03d}] Done in {elapsed:.1f}s — {len(hazards)} hazards")
    for h in hazards:
        print(f"       {h.get('category', '?')} sev={h.get('severity', '?')}: {h.get('description', '')[:60]}")

    return idx, hazards


def main():
    parser = argparse.ArgumentParser(description="Run Gemini analysis on pre-chunked dashcam video")
    parser.add_argument("--limit", type=int, default=0, help="Only analyze first N chunks (0 = all)")
    parser.add_argument("--resume", action="store_true", help="Skip already-analyzed chunks")
    parser.add_argument("--workers", type=int, default=3, help="Parallel workers (default: 3)")
    parser.add_argument("--model", type=str, default="gemini-3-pro-preview", help="Gemini model name")
    parser.add_argument("--save-every", type=int, default=5, help="Save results every N chunks")
    args = parser.parse_args()

    # Verify API key
    if not os.environ.get("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY not set in .env")
        sys.exit(1)

    # Load manifest
    chunks = load_manifest()
    total = len(chunks)
    print(f"Loaded manifest: {total} chunks")

    # Apply limit
    if args.limit > 0:
        chunks = chunks[:args.limit]
        print(f"Limiting to first {args.limit} chunks")

    # Resume support
    chunk_results = {}
    if args.resume:
        existing = load_partial_results()
        chunk_results = {int(k): v for k, v in existing.get("chunk_results", {}).items()}
        already_done = set(chunk_results.keys())
        chunks = [c for c in chunks if c["chunk_index"] not in already_done]
        print(f"Resuming: {len(already_done)} already done, {len(chunks)} remaining")

    if not chunks:
        print("Nothing to analyze. All chunks already processed.")
        sys.exit(0)

    # Run analysis
    print(f"\nStarting analysis: {len(chunks)} chunks, {args.workers} workers, model={args.model}")
    print("=" * 60)

    t_start = time.time()
    completed = 0

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(process_chunk, chunk, args.model): chunk
            for chunk in chunks
        }

        for future in as_completed(futures):
            idx, hazards = future.result()
            chunk_results[idx] = hazards
            completed += 1

            # Incremental save
            if completed % args.save_every == 0:
                all_hazards_so_far = [h for hs in chunk_results.values() for h in hs]
                save_results(chunk_results, all_hazards_so_far)
                print(f"  --- Saved progress ({completed}/{len(chunks)} chunks) ---")

    elapsed = time.time() - t_start
    print("=" * 60)
    print(f"Analysis complete in {elapsed:.1f}s")

    # Collect all hazards
    all_hazards = [h for idx in sorted(chunk_results.keys()) for h in chunk_results[idx]]
    print(f"Total raw hazards: {len(all_hazards)}")

    # Deduplicate
    deduped = deduplicate_hazards(all_hazards)
    print(f"After deduplication: {len(deduped)} unique hazards")

    # Generate route summary
    print("\nGenerating route summary with Gemini...")
    try:
        summary = generate_route_summary(deduped, model_name=args.model)
        print(f"Route quality score: {summary.get('route_quality_score', 'N/A')}/10")
    except Exception as e:
        print(f"Summary generation failed: {e}")
        summary = {
            "route_quality_score": 0,
            "total_hazards": len(deduped),
            "hazard_breakdown": {},
            "severity_distribution": {},
            "worst_segment": {},
            "route_briefing": "Summary generation failed.",
        }

    # Final save
    save_results(chunk_results, deduped, summary)
    print(f"\nResults saved to {RESULTS_PATH}")
    print(f"Run 'python server.py' and select 'output_compressed' in the UI to view.")


if __name__ == "__main__":
    main()
