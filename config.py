import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
WORKFLOW_DIR = BASE_DIR / "workflow_templates"
OUTPUT_DIR = BASE_DIR / "outputs"
WORKFLOW_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COMFYUI_BASE = Path(
    os.getenv("COMFYUI_PATH",
              r"C:\Users\sagarwave\ComfyUI-Installs\ComfyUI (1)\ComfyUI")
)

HF_TOKEN = os.getenv("HF_TOKEN", "")
COMFYUI_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
COMFYUI_INPUT = COMFYUI_BASE / "input"
COMFYUI_OUTPUT = COMFYUI_BASE / "output"
COMFYUI_MODELS = COMFYUI_BASE / "models"

# LLM Configuration - OpenCode Zen (Free DeepSeek V4 Flash)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "opencode_zen")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v4-flash-free")
OPENCODE_ZEN_API_KEY = os.getenv("OPENCODE_ZEN_API_KEY",
    "sk-qmd6okPEqt0zwaVY7cuDHrSnKMXd4P1aA2Ko8zit7LRYbgggFGEcyoFKbpqi1Gsj")
OPENCODE_ZEN_BASE_URL = os.getenv("OPENCODE_ZEN_BASE_URL",
    "https://opencode.ai/zen/v1")

# News Studio config
SUPPORTED_LANGUAGES = {
    "English": "en", "Hindi": "hi", "Marathi": "mr",
    "Gujarati": "gu",
}

REEL_DURATIONS = {
    "Short (15-30s)": (15, 30),
    "Medium (30-60s)": (30, 60),
    "Long (1-3 min)": (60, 180),
    "Extended (3-5 min)": (180, 300),
}

RESOLUTIONS = {
    "Vertical (9:16) - Reels": (1080, 1920),
    "Horizontal (16:9)": (1920, 1080),
    "Square (1:1)": (1080, 1080),
}

# Quality defaults
QUALITY_PRESETS = {
    "draft": {"steps": 15, "cfg": 5.0, "sampler": "euler", "scheduler": "normal", "bitrate": "2M"},
    "standard": {"steps": 25, "cfg": 7.0, "sampler": "dpmpp_2m", "scheduler": "karras", "bitrate": "4M"},
    "professional": {"steps": 30, "cfg": 7.5, "sampler": "dpmpp_2m", "scheduler": "karras", "bitrate": "8M"},
    "broadcast": {"steps": 35, "cfg": 8.0, "sampler": "dpmpp_3m_sde", "scheduler": "karras", "bitrate": "12M"},
}

DEFAULT_QUALITY = "professional"

DEFAULT_MOOD = "informational"

MOOD_THEMES = {
    "breaking": {
        "name": "Breaking News",
        "ticker_bg": (200, 30, 30),
        "lower_third_bg": (160, 20, 20),
        "lower_third_accent": (255, 200, 50),
        "lower_third_text": (255, 255, 255),
        "brand_color": (212, 160, 23),
        "gold_bar": (255, 200, 50),
        "overlay_opacity": 0.30,
        "transition_speed": "fast",
        "visual_prefix": "dramatic breaking news, emergency coverage, urgent atmosphere, high contrast lighting, intense colors, red and blue emergency lights, fast-paced cinematic",
        "subtitle_color": (255, 255, 255),
        "subtitle_stroke": (180, 30, 30),
    },
    "serious": {
        "name": "Serious News",
        "ticker_bg": (20, 50, 120),
        "lower_third_bg": (0, 40, 100),
        "lower_third_accent": (180, 160, 30),
        "lower_third_text": (255, 255, 255),
        "brand_color": (212, 160, 23),
        "gold_bar": (180, 160, 30),
        "overlay_opacity": 0.35,
        "transition_speed": "normal",
        "visual_prefix": "professional serious news, formal broadcast quality, authoritative atmosphere, structured composition, navy blue tones, studio lighting, corporate professional",
        "subtitle_color": (255, 255, 255),
        "subtitle_stroke": (0, 40, 80),
    },
    "sad": {
        "name": "Sad News",
        "ticker_bg": (30, 40, 80),
        "lower_third_bg": (20, 30, 60),
        "lower_third_accent": (100, 120, 160),
        "lower_third_text": (220, 220, 230),
        "brand_color": (150, 160, 180),
        "gold_bar": (100, 120, 160),
        "overlay_opacity": 0.40,
        "transition_speed": "slow",
        "visual_prefix": "somber respectful mood, soft diffused lighting, muted cool tones, gentle shadows, emotional atmosphere, dark blue and gray palette, pensive composition",
        "subtitle_color": (220, 220, 230),
        "subtitle_stroke": (20, 30, 60),
    },
    "inspirational": {
        "name": "Inspirational",
        "ticker_bg": (180, 120, 20),
        "lower_third_bg": (140, 90, 15),
        "lower_third_accent": (255, 215, 0),
        "lower_third_text": (255, 255, 255),
        "brand_color": (255, 215, 0),
        "gold_bar": (255, 215, 0),
        "overlay_opacity": 0.25,
        "transition_speed": "normal",
        "visual_prefix": "uplifting positive news, warm golden hour lighting, vibrant cheerful colors, hopeful atmosphere, bright sunny tones, optimistic composition, celebrating success",
        "subtitle_color": (255, 255, 255),
        "subtitle_stroke": (140, 90, 15),
    },
    "informational": {
        "name": "Informational",
        "ticker_bg": (0, 60, 120),
        "lower_third_bg": (0, 40, 100),
        "lower_third_accent": (212, 160, 23),
        "lower_third_text": (255, 255, 255),
        "brand_color": (212, 160, 23),
        "gold_bar": (212, 160, 23),
        "overlay_opacity": 0.35,
        "transition_speed": "normal",
        "visual_prefix": "professional broadcast quality, balanced neutral lighting, clear crisp visuals, news studio production, well-lit scene, factual documentary style",
        "subtitle_color": (255, 255, 255),
        "subtitle_stroke": (0, 40, 80),
    },
}

# Model paths
T2I_MODEL = "sd_xl_base_1.0.safetensors"
VIDEO_MODEL = "flux1-dev.safetensors"
FACE_MODEL = "LivePortrait"

# TTS
TTS_CHUNK_LIMIT = 3000
TTS_VOICES = {
    "English": "en-IN-NeerjaNeural",
    "Hindi": "hi-IN-SwaraNeural",
    "Marathi": "mr-IN-AarohiNeural",
    "Gujarati": "gu-IN-DhwaniNeural",
}
