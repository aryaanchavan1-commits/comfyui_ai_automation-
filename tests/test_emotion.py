import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from emotion_analyzer import (
    MOOD_DESCRIPTIONS, MOOD_COLORS, MOOD_VISUAL_PREFIXES,
    analyze_mood_from_text, _fallback_mood,
)


def test_mood_descriptions():
    expected_moods = {"breaking", "serious", "sad", "inspirational", "informational"}
    assert set(MOOD_DESCRIPTIONS.keys()) == expected_moods
    for mood, desc in MOOD_DESCRIPTIONS.items():
        assert isinstance(desc, str)
        assert len(desc) > 10


def test_mood_colors():
    assert set(MOOD_COLORS.keys()) == set(MOOD_DESCRIPTIONS.keys())
    for mood, colors in MOOD_COLORS.items():
        for key in ("primary", "secondary", "accent", "text"):
            assert key in colors
            r, g, b = colors[key]
            assert 0 <= r <= 255
            assert 0 <= g <= 255
            assert 0 <= b <= 255


def test_mood_visual_prefixes():
    assert set(MOOD_VISUAL_PREFIXES.keys()) == set(MOOD_DESCRIPTIONS.keys())
    for mood, prefix in MOOD_VISUAL_PREFIXES.items():
        assert isinstance(prefix, str)
        assert len(prefix) > 20


def test_fallback_mood_breaking():
    result = _fallback_mood("Breaking news: urgent crisis emergency disaster")
    assert result["mood"] == "breaking"
    assert result["confidence"] > 0.5


def test_fallback_mood_sad():
    result = _fallback_mood("Tragic death of victims in fatal accident")
    assert result["mood"] == "sad"
    assert result["confidence"] > 0.5


def test_fallback_mood_inspirational():
    result = _fallback_mood("Inspiring breakthrough success and victory celebration")
    assert result["mood"] == "inspirational"
    assert result["confidence"] > 0.5


def test_fallback_mood_serious():
    result = _fallback_mood("Government official political investigation court")
    assert result["mood"] == "serious"
    assert result["confidence"] > 0.5


def test_fallback_mood_informational():
    result = _fallback_mood("The weather today is sunny with mild temperatures")
    assert result["mood"] == "informational"
    assert result["confidence"] == 0.5


def test_analyze_mood_fallback():
    result = analyze_mood_from_text("", "general news")
    assert result["mood"] in MOOD_DESCRIPTIONS
    assert 0 <= result["confidence"] <= 1
