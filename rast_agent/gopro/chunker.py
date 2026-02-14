"""
Video chunker — splits GoPro MP4 into segments using ffmpeg.

Produces fixed-duration chunks with configurable overlap and
writes a chunks_manifest.json describing each segment.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Optional


def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            video_path,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr.strip()}")
    return float(result.stdout.strip())


def chunk_video(
    input_path: str,
    output_dir: str,
    chunk_duration: int = 20,
    overlap: int = 3,
) -> List[Dict]:
    """
    Split a video into chunks with overlap.

    Args:
        input_path: Path to the source MP4 file.
        output_dir: Directory to write chunk files.
        chunk_duration: Duration of each chunk in seconds.
        overlap: Overlap between consecutive chunks in seconds.

    Returns:
        List of chunk manifest entries, each with:
        - chunk_index: int
        - file_path: str (absolute path)
        - start_sec: float
        - end_sec: float
        - overlap_sec: int
    """
    input_path = os.path.abspath(input_path)
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    total_duration = get_video_duration(input_path)
    basename = Path(input_path).stem

    chunks = []
    chunk_index = 0
    start = 0.0
    step = chunk_duration - overlap

    while start < total_duration:
        end = min(start + chunk_duration, total_duration)
        out_file = os.path.join(
            output_dir,
            f"{basename}_chunk_{chunk_index:03d}.mp4",
        )

        # Use ffmpeg stream copy for speed (no re-encoding)
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss", str(start),
                "-i", input_path,
                "-t", str(end - start),
                "-c", "copy",
                "-f", "mp4",
                out_file,
            ],
            capture_output=True,
            timeout=120,
        )

        chunks.append({
            "chunk_index": chunk_index,
            "file_path": out_file,
            "start_sec": start,
            "end_sec": end,
            "overlap_sec": overlap if chunk_index > 0 else 0,
        })

        chunk_index += 1
        start += step

        # Avoid tiny trailing chunks (< 5s)
        if total_duration - (start + step) < 5 and start < total_duration:
            pass  # let the next iteration create a slightly longer final chunk

    # Write manifest
    manifest_path = os.path.join(output_dir, "chunks_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(
            {
                "source": input_path,
                "total_duration": total_duration,
                "chunk_duration": chunk_duration,
                "overlap": overlap,
                "chunks": chunks,
            },
            f,
            indent=2,
        )

    return chunks


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python chunker.py <input.mp4> <output_dir> [chunk_sec] [overlap_sec]")
        sys.exit(1)

    inp = sys.argv[1]
    out = sys.argv[2]
    dur = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    ovl = int(sys.argv[4]) if len(sys.argv) > 4 else 3

    result = chunk_video(inp, out, dur, ovl)
    print(f"Created {len(result)} chunks in {out}")
    for c in result:
        print(f"  [{c['chunk_index']:03d}] {c['start_sec']:.1f}s - {c['end_sec']:.1f}s")
