"""
Flask server for RoadSense — serves the frontend SPA and cached data.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory, send_file, abort

load_dotenv()

app = Flask(
    __name__,
    static_folder="frontend/static",
    template_folder="frontend/templates",
)

CACHE_DIR = Path(__file__).parent / "cache"
DATA_DIR = Path(__file__).parent / "data"


@app.route("/")
def index():
    return send_file("frontend/templates/index.html")


@app.route("/api/reports")
def list_reports():
    """List all cached analysis reports."""
    reports = []
    if CACHE_DIR.exists():
        for f in sorted(CACHE_DIR.glob("*_results.json")):
            try:
                with open(f) as fh:
                    data = json.load(fh)
                reports.append({
                    "name": f.stem.replace("_results", ""),
                    "file": f.name,
                    "total_hazards": len(data.get("hazards", [])),
                    "quality_score": data.get("summary", {}).get("route_quality_score"),
                })
            except Exception:
                continue
    return jsonify(reports)


@app.route("/api/report/<filename>")
def get_report(filename):
    """Get a specific analysis report."""
    path = CACHE_DIR / filename
    if not path.exists() or not path.is_file():
        abort(404)
    return send_file(path, mimetype="application/json")


@app.route("/api/video/<path:filename>")
def serve_video(filename):
    """Serve video files from cache/chunks/ or data/ directory."""
    # Try cache/chunks first
    for base in [CACHE_DIR / "chunks", DATA_DIR, Path(".")]:
        full = base / filename
        if full.exists() and full.is_file():
            return send_file(str(full), mimetype="video/mp4")
    abort(404)


@app.route("/api/config")
def get_config():
    """Return frontend configuration (non-secret)."""
    return jsonify({
        "google_maps_api_key": os.getenv("GOOGLE_MAPS_API_KEY", ""),
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
