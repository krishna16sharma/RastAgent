"""
GoPro telemetry parser — bridges Node.js gopro-parser.js with Python.

Calls the Node.js parser via subprocess to extract GPS telemetry
from GoPro MP4 files (GPMF format).
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Optional


# Path to the Node.js parser script
_PARSER_JS = Path(__file__).resolve().parents[2] / "utils" / "gopro-parser.js"

# Inline Node.js script that imports the parser and dumps JSON
_EXTRACT_SCRIPT = """
const parser = require('{parser_path}');

async function main() {{
    const filePath = process.argv[2];
    const lockedOnly = process.argv[3] === 'true';
    const minFix = parseInt(process.argv[4] || '2', 10);

    const result = await parser.parseFile(filePath, {{
        streams: ['GPS5'],
        lockedOnly,
        minFix,
    }});

    const output = {{
        gps: result.gps,
        available_streams: result.availableStreams,
    }};

    process.stdout.write(JSON.stringify(output));
}}

main().catch(err => {{
    process.stderr.write(err.message);
    process.exit(1);
}});
"""


def extract_gps(
    mp4_path: str,
    locked_only: bool = True,
    min_fix: int = 2,
    node_bin: str = "node",
) -> List[Dict]:
    """
    Extract GPS samples from a GoPro MP4 file.

    Args:
        mp4_path: Path to the GoPro MP4 file.
        locked_only: Only return samples with GPS fix.
        min_fix: Minimum fix value (2=2D, 3=3D).
        node_bin: Path to the Node.js binary.

    Returns:
        List of GPS samples, each with keys:
        lat, lon, alt, speed2d, speed3d, date, cts, fix, precision
    """
    mp4_path = os.path.abspath(mp4_path)
    if not os.path.isfile(mp4_path):
        raise FileNotFoundError(f"MP4 file not found: {mp4_path}")

    # Check node_modules exist next to the parser
    parser_dir = _PARSER_JS.parent
    node_modules = parser_dir / "node_modules"
    if not node_modules.is_dir():
        raise RuntimeError(
            f"Node modules not found at {node_modules}. "
            f"Run 'npm install' in {parser_dir}"
        )

    # Write inline script to a temp file
    script_content = _EXTRACT_SCRIPT.format(
        parser_path=str(_PARSER_JS).replace("\\", "/")
    )

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".js", delete=False, dir=str(parser_dir)
    ) as f:
        f.write(script_content)
        script_path = f.name

    try:
        result = subprocess.run(
            [
                node_bin,
                script_path,
                mp4_path,
                str(locked_only).lower(),
                str(min_fix),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(parser_dir),
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"GPS extraction failed: {result.stderr.strip()}"
            )

        data = json.loads(result.stdout)
        return data["gps"]

    finally:
        os.unlink(script_path)


def extract_gps_as_trace(
    mp4_path: str,
    locked_only: bool = True,
    min_fix: int = 2,
) -> List[Dict]:
    """
    Extract GPS and return in the trace format used by RouteMatcher.

    Returns:
        List of dicts with keys: lat, lng, timestamp (cts in ms)
    """
    samples = extract_gps(mp4_path, locked_only, min_fix)
    return [
        {
            "lat": s["lat"],
            "lng": s["lon"],
            "timestamp": s["cts"],
        }
        for s in samples
    ]


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python parser.py <gopro.mp4>")
        sys.exit(1)

    samples = extract_gps(sys.argv[1])
    print(f"Extracted {len(samples)} GPS samples")
    if samples:
        print(f"First: {json.dumps(samples[0], indent=2)}")
        print(f"Last:  {json.dumps(samples[-1], indent=2)}")
