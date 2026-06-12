import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    BASE_DIR, WORKFLOW_DIR, OUTPUT_DIR, COMFYUI_URL,
    SUPPORTED_LANGUAGES, REEL_DURATIONS, RESOLUTIONS,
    MOOD_THEMES, DEFAULT_MOOD, QUALITY_PRESETS, DEFAULT_QUALITY,
    LLM_PROVIDER, LLM_MODEL,
)


def test_directories_exist():
    assert WORKFLOW_DIR.exists()
    assert OUTPUT_DIR.exists()


def test_supported_languages():
    assert "English" in SUPPORTED_LANGUAGES
    assert "Hindi" in SUPPORTED_LANGUAGES
    assert "Marathi" in SUPPORTED_LANGUAGES
    assert "Gujarati" in SUPPORTED_LANGUAGES
    assert len(SUPPORTED_LANGUAGES) == 4


def test_reel_durations():
    assert "Short (15-30s)" in REEL_DURATIONS
    assert "Medium (30-60s)" in REEL_DURATIONS
    for key, (lo, hi) in REEL_DURATIONS.items():
        assert isinstance(lo, int)
        assert isinstance(hi, int)
        assert lo < hi


def test_resolutions():
    for name, (w, h) in RESOLUTIONS.items():
        assert isinstance(w, int) and w > 0
        assert isinstance(h, int) and h > 0


def test_mood_themes():
    assert DEFAULT_MOOD in MOOD_THEMES
    for mood, theme in MOOD_THEMES.items():
        assert "name" in theme
        assert "visual_prefix" in theme
        assert "ticker_bg" in theme
        assert "lower_third_bg" in theme
        assert "overlay_opacity" in theme
        assert 0 <= theme["overlay_opacity"] <= 1


def test_quality_presets():
    assert DEFAULT_QUALITY in QUALITY_PRESETS
    for name, params in QUALITY_PRESETS.items():
        assert "steps" in params
        assert "cfg" in params
        assert "sampler" in params
        assert "scheduler" in params
        assert params["steps"] > 0
        assert params["cfg"] > 0


def test_llm_config():
    assert LLM_PROVIDER == "opencode_zen"
    assert LLM_MODEL == "deepseek-v4-flash-free"


def test_comfyui_url():
    assert COMFYUI_URL.startswith("http")
