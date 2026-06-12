import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline_manager import PipelineManager
from config import MOOD_THEMES, DEFAULT_MOOD


def test_pipeline_initial_state():
    pipeline = PipelineManager(None, None)
    state = pipeline.get_state()
    assert state["status"] == "idle"
    assert state["steps"] == []
    assert state["error"] is None


def test_set_mood_valid():
    pipeline = PipelineManager(None, None)
    for mood in MOOD_THEMES:
        pipeline.set_mood(mood)
        assert pipeline.mood == mood


def test_set_mood_invalid():
    pipeline = PipelineManager(None, None)
    pipeline.set_mood("nonexistent_mood")
    assert pipeline.mood == DEFAULT_MOOD


def test_get_theme():
    pipeline = PipelineManager(None, None)
    theme = pipeline._get_theme()
    assert "name" in theme
    assert "visual_prefix" in theme


def test_get_theme_for_mood():
    pipeline = PipelineManager(None, None)
    for mood in MOOD_THEMES:
        pipeline.set_mood(mood)
        theme = pipeline._get_theme()
        assert theme["name"] == MOOD_THEMES[mood]["name"]


def test_assemble_script():
    pipeline = PipelineManager(None, None)
    script = {
        "headline": "HEADLINE",
        "introduction": "INTRO",
        "main_story": "STORY",
        "highlights": ["H1", "H2"],
        "conclusion": "CONCLUSION",
    }
    result = pipeline._assemble_script(script)
    assert "HEADLINE" in result
    assert "INTRO" in result
    assert "STORY" in result
    assert "H1" in result
    assert "CONCLUSION" in result
