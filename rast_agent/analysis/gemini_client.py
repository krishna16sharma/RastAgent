"""
Gemini API client for RoadSense hazard analysis.

Uses the google.genai SDK (Gen AI SDK) to send video chunks
to Gemini 3 Pro for hazard detection and route summary generation.
"""

import json
import os
import time
from pathlib import Path
from typing import List, Dict

from dotenv import load_dotenv

load_dotenv()

_client = None

DEFAULT_MODEL = "gemini-3-pro-preview"


def _get_client():
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


# Prompt file paths
_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
_SYSTEM_PROMPT = _PROMPTS_DIR / "system_prompt.md"
_CHUNK_PROMPT = _PROMPTS_DIR / "chunk_analysis_prompt.md"
_SUMMARY_PROMPT = _PROMPTS_DIR / "route_summary_prompt.md"


def _load_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _build_chunk_prompt(chunk_index: int, start_time: float, end_time: float) -> str:
    """Build the chunk analysis prompt with template variables filled in."""
    template = _load_prompt(_CHUNK_PROMPT)
    return (
        template
        .replace("{chunk_index}", str(chunk_index))
        .replace("{start_time}", f"{start_time:.1f}")
        .replace("{end_time}", f"{end_time:.1f}")
    )


def analyze_chunk(
    video_path: str,
    chunk_index: int,
    start_time: float,
    end_time: float,
    model_name: str = DEFAULT_MODEL,
) -> List[Dict]:
    """
    Send a video chunk to Gemini for hazard analysis.

    Args:
        video_path: Path to the video chunk MP4.
        chunk_index: Zero-based chunk index.
        start_time: Start time in seconds.
        end_time: End time in seconds.
        model_name: Gemini model to use.

    Returns:
        List of hazard annotation dicts (or empty list).
    """
    from google.genai import types

    client = _get_client()

    # Upload the video file
    video_file = client.files.upload(
        file=video_path,
        config=types.UploadFileConfig(mime_type="video/mp4"),
    )

    # Wait for file to be processed
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = client.files.get(name=video_file.name)

    if video_file.state.name == "FAILED":
        raise RuntimeError(f"Video upload failed for {video_path}")

    # Build prompts
    system_prompt = _load_prompt(_SYSTEM_PROMPT)
    chunk_prompt = _build_chunk_prompt(chunk_index, start_time, end_time)

    # Generate content
    response = client.models.generate_content(
        model=model_name,
        contents=[
            types.Part.from_uri(file_uri=video_file.uri, mime_type="video/mp4"),
            chunk_prompt,
        ],
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
        ),
    )

    # Parse JSON response
    text = response.text.strip()
    hazards = json.loads(text)

    # Ensure it's a list
    if isinstance(hazards, dict):
        hazards = [hazards]

    # Clean up uploaded file
    try:
        client.files.delete(name=video_file.name)
    except Exception:
        pass

    return hazards


def generate_route_summary(
    hazards: List[Dict],
    model_name: str = DEFAULT_MODEL,
) -> Dict:
    """
    Generate a route quality summary from all detected hazards.

    Args:
        hazards: List of hazard dicts with gps coordinates mapped.
        model_name: Gemini model to use.

    Returns:
        Route summary dict with quality score, breakdown, briefing.
    """
    from google.genai import types

    client = _get_client()

    system_prompt = _load_prompt(_SYSTEM_PROMPT)
    summary_prompt = _load_prompt(_SUMMARY_PROMPT)

    # Append the hazard data to the prompt
    full_prompt = (
        summary_prompt
        + "\n\n## Hazard Data\n\n```json\n"
        + json.dumps(hazards, indent=2)
        + "\n```"
    )

    response = client.models.generate_content(
        model=model_name,
        contents=full_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
        ),
    )

    return json.loads(response.text.strip())
