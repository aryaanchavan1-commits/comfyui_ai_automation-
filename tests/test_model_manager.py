import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from model_manager import MODEL_FOLDER_MAP, MODEL_HINT_KEYWORDS, RECOMMENDED_MODELS


def test_model_folder_map():
    assert "checkpoint" in MODEL_FOLDER_MAP
    assert MODEL_FOLDER_MAP["checkpoint"] == "checkpoints"
    assert MODEL_FOLDER_MAP["lora"] == "loras"
    assert MODEL_FOLDER_MAP["vae"] == "vae"


def test_model_hint_keywords():
    assert "checkpoints" in MODEL_HINT_KEYWORDS
    assert "loras" in MODEL_HINT_KEYWORDS
    assert "vae" in MODEL_HINT_KEYWORDS
    for folder, keywords in MODEL_HINT_KEYWORDS.items():
        assert len(keywords) > 0


def test_recommended_models_structure():
    assert "checkpoints" in RECOMMENDED_MODELS
    assert "loras" in RECOMMENDED_MODELS
    assert "vae" in RECOMMENDED_MODELS
    for folder, models in RECOMMENDED_MODELS.items():
        for name, url in models.items():
            assert isinstance(name, str)
            assert url.startswith("http")


def test_recommended_models_has_sdxl():
    checkpoints = RECOMMENDED_MODELS["checkpoints"]
    names = [n.lower() for n in checkpoints.keys()]
    assert any("sdxl" in n or "xl" in n for n in names)
    assert any("flux" in n for n in names)
