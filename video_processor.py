import os
import time
import json
import logging
import typing
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- Configuration ---
load_dotenv()  # Load environment variables from .env

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# Constants
API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = "gemini-2.0-flash"  # Flash is excellent for video/frame analysis
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "inference_output"
PROMPT_PATH = PROJECT_ROOT / "context_prompt" / "prompt.md"

def setup_client():
    """Configures the Gemini API client."""
    if not API_KEY:
        raise ValueError("GOOGLE_API_KEY not found. Please check your .env file.")
    genai.configure(api_key=API_KEY)

def load_system_prompt(path: Path) -> str:
    """Reads the system instruction from the markdown file."""
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found at: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

def clean_json_response(raw_text: str) -> dict:
    """
    Cleans the model output to extract pure JSON.
    Removes markdown code blocks (```json ... ```) if present.
    """
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        # Remove first line (```json) and last line (```)
        cleaned = "\n".join(cleaned.splitlines()[1:-1])
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        logger.debug(f"Raw response: {raw_text}")
        return {"error": "Invalid JSON", "raw_content": raw_text}

def wait_for_video_processing(file_upload):
    """Polls the API until the video is ready for inference."""
    logger.info(f"Processing video: {file_upload.name}...")
    while file_upload.state.name == "PROCESSING":
        time.sleep(2)
        file_upload = genai.get_file(file_upload.name)
    
    if file_upload.state.name == "FAILED":
        raise RuntimeError(f"Video processing failed for {file_upload.name}")
    
    logger.info(f"Video ready: {file_upload.name}")
    return file_upload

def process_video_pipeline():
    """Main pipeline execution."""
    setup_client()
    
    # 1. Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 2. Load System Prompt
    try:
        system_instruction = load_system_prompt(PROMPT_PATH)
        logger.info("System prompt loaded successfully.")
    except Exception as e:
        logger.error(f"Critical error loading prompt: {e}")
        return

    # 3. Initialize Model
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=system_instruction
    )

    # 4. Iterate through videos in /data
    video_extensions = {".mp4", ".mov", ".avi", ".mkv"}
    video_files = [p for p in DATA_DIR.iterdir() if p.suffix.lower() in video_extensions]

    if not video_files:
        logger.warning(f"No video files found in {DATA_DIR}")
        return

    logger.info(f"Found {len(video_files)} videos to process.")

    for video_path in video_files:
        output_path = OUTPUT_DIR / f"{video_path.stem}.json"

        # Skip if already processed
        if output_path.exists():
            logger.info(f"Skipping {video_path.name} (Output already exists)")
            continue

        try:
            # Upload Video
            logger.info(f"Uploading {video_path.name}...")
            video_file = genai.upload_file(path=video_path)
            
            # Wait for processing
            video_file = wait_for_video_processing(video_file)

            # Generate Content
            logger.info(f"Analyzing infrastructure for {video_path.name}...")
            
            # Note: The system prompt is already set in the model config.
            # We just send the video file as the user message.
            response = model.generate_content(
                [video_file],
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json", # Forces strict JSON
                    temperature=0.2 # Lower temperature for factual auditing
                )
            )

            # Parse and Save
            result_json = clean_json_response(response.text)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result_json, f, indent=2)
            
            logger.info(f"Success! Saved analysis to {output_path.name}")

            # Cleanup: Delete file from Cloud storage to save space/quota
            video_file.delete()

        except Exception as e:
            logger.error(f"Failed to process {video_path.name}: {e}")

if __name__ == "__main__":
    process_video_pipeline()