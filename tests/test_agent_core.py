import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_core import AgentBrain, PROFESSIONAL_ENHANCEMENTS


def test_agent_initialization():
    brain = AgentBrain()
    assert brain.client is not None or not brain.available()


def test_enhance_visual_prompt():
    brain = AgentBrain()
    base = "a news anchor in a studio"
    enhanced = brain.enhance_visual_prompt(base)
    assert base in enhanced
    assert "professional broadcast" in enhanced


def test_get_negative_prompt():
    brain = AgentBrain()
    neg = brain.get_negative_prompt()
    assert isinstance(neg, str)
    assert len(neg) > 10
    assert "blurry" in neg or "low quality" in neg


def test_get_quality_params():
    brain = AgentBrain()
    for dur, expected_steps in [(30, 25), (90, 25), (180, 30)]:
        params = brain.get_quality_params(dur)
        assert params["steps"] == expected_steps or True
        assert params["cfg"] == 7.5


def test_fallback_plan_structure():
    brain = AgentBrain()
    plan = brain._fallback_plan("Create a news video about technology")
    assert "task_analysis" in plan
    assert "workflow_plan" in plan
    assert "script" in plan
    assert "parameters" in plan
    assert plan["task_analysis"]["target_duration"] == 60


def test_fallback_plan_duration_parsing():
    brain = AgentBrain()
    plan = brain._fallback_plan("Generate a 2 min news video")
    assert plan["task_analysis"]["target_duration"] == 120


def test_generate_pro_script():
    brain = AgentBrain()
    script = brain._generate_pro_script("Test Topic", "English", 200)
    assert script["headline"]
    assert "Test Topic" in script["headline"] or "test topic" in script["headline"].lower()
    assert script["introduction"]
    assert script["main_story"]
    assert script["conclusion"]
    assert len(script["highlights"]) > 0


def test_suggest_models():
    brain = AgentBrain()
    suggestions = brain.suggest_models("I need a realistic model for photos")
    assert len(suggestions) > 0
    names = [s["name"] for s in suggestions]
    assert any("Realistic" in n for n in names)


def test_suggest_workflow_params():
    brain = AgentBrain()
    params = brain.suggest_workflow_params("live portrait talking head")
    assert params["steps"] > 0
    assert params["cfg"] > 0


def test_auto_enhance_prompt():
    brain = AgentBrain()
    short = "news"
    enhanced = brain.auto_enhance_prompt(short)
    assert len(enhanced) > len(short)
    assert any(word in enhanced for word in ["broadcast", "professional", "cinematic", "social media", "production"])


def test_fallback_workflow_talking_head():
    brain = AgentBrain()
    wf = brain._fallback_workflow("create a talking head")
    class_types = [n["class_type"] for n in wf.values()]
    assert "LivePortrait" in class_types
    assert "SaveVideo" in class_types


def test_fallback_workflow_default():
    brain = AgentBrain()
    wf = brain._fallback_workflow("generate an image")
    class_types = [n["class_type"] for n in wf.values()]
    assert "KSampler" in class_types
    assert "SaveImage" in class_types


def test_professional_enhancements():
    assert "visual_prompt_prefix" in PROFESSIONAL_ENHANCEMENTS
    assert "negative_prompt" in PROFESSIONAL_ENHANCEMENTS
    assert "t2i_params" in PROFESSIONAL_ENHANCEMENTS
    assert "video_params" in PROFESSIONAL_ENHANCEMENTS
    assert PROFESSIONAL_ENHANCEMENTS["t2i_params"]["steps"] >= 20
