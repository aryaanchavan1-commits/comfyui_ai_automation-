import os
import re
import json
import tempfile
from pathlib import Path
from faster_whisper import WhisperModel
from config import LLM_MODEL, OPENCODE_ZEN_API_KEY, OPENCODE_ZEN_BASE_URL

MOOD_DESCRIPTIONS = {
    "breaking": "Urgent breaking news — dramatic, fast-paced, high-contrast visuals, red highlights, urgent tone",
    "serious": "Serious professional news — navy blue tones, structured overlays, formal presentation, authoritative",
    "sad": "Sad or tragic news — dimmed lighting, blue/dark tones, slower transitions, respectful atmosphere",
    "inspirational": "Inspirational good news — warm golden/amber tones, uplifting pacing, bright optimistic visuals",
    "informational": "Neutral informational news — standard broadcast presentation, balanced colors, clear and calm",
}

MOOD_COLORS = {
    "breaking": {"primary": (200, 30, 30), "secondary": (180, 20, 20), "accent": (255, 200, 50), "text": (255, 255, 255)},
    "serious": {"primary": (20, 50, 120), "secondary": (0, 40, 100), "accent": (180, 160, 30), "text": (255, 255, 255)},
    "sad": {"primary": (30, 40, 80), "secondary": (20, 30, 60), "accent": (100, 120, 160), "text": (220, 220, 230)},
    "inspirational": {"primary": (180, 120, 20), "secondary": (160, 100, 10), "accent": (255, 215, 0), "text": (255, 255, 255)},
    "informational": {"primary": (0, 60, 120), "secondary": (0, 50, 100), "accent": (200, 170, 50), "text": (255, 255, 255)},
}

MOOD_VISUAL_PREFIXES = {
    "breaking": "dramatic breaking news, emergency coverage, urgent atmosphere, high contrast lighting, intense colors, red and blue emergency lights, fast-paced cinematic",
    "serious": "professional serious news, formal broadcast quality, authoritative atmosphere, structured composition, navy blue tones, studio lighting, corporate professional",
    "sad": "somber respectful mood, soft diffused lighting, muted cool tones, gentle shadows, emotional atmosphere, dark blue and gray palette, pensive composition",
    "inspirational": "uplifting positive news, warm golden hour lighting, vibrant cheerful colors, hopeful atmosphere, bright sunny tones, optimistic composition, celebrating success",
    "informational": "professional broadcast quality, balanced neutral lighting, clear crisp visuals, news studio production, well-lit scene, factual documentary style",
}

WHISPER_MODEL = None


def _get_whisper():
    global WHISPER_MODEL
    if WHISPER_MODEL is None:
        WHISPER_MODEL = WhisperModel("tiny", device="cpu", compute_type="int8")
    return WHISPER_MODEL


def transcribe_audio(audio_path: str) -> str:
    if not audio_path or not os.path.exists(audio_path):
        return ""
    try:
        model = _get_whisper()
        segments, _ = model.transcribe(audio_path, beam_size=1, language=None)
        return " ".join(seg.text for seg in segments)
    except Exception:
        return ""


def analyze_mood_from_text(text: str, topic: str = "") -> dict:
    text_to_analyze = text or topic or "general news"
    try:
        if OPENCODE_ZEN_API_KEY:
            from openai import OpenAI
            client = OpenAI(api_key=OPENCODE_ZEN_API_KEY, base_url=OPENCODE_ZEN_BASE_URL)
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": f"""You are a news mood analyzer.
Analyze the emotional tone of the text below and classify it into EXACTLY one mood:
- breaking: urgent, dramatic, emergency, crisis, breaking news, disaster
- serious: important, significant, political, legal, formal, investigative
- sad: tragic, loss, death, unfortunate, mournful, heartbreaking
- inspirational: positive, success, achievement, celebration, hopeful, uplifting
- informational: neutral, factual, report, update, general news

Respond with ONLY valid JSON:
{{"mood": "one_of_the_above", "confidence": 0.0-1.0, "reason": "brief reason"}}"""},
                    {"role": "user", "content": f"Text to analyze:\n\n{text_to_analyze[:2000]}"}
                ],
                temperature=0.1,
                max_tokens=256,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.choices[0].message.content)
            mood = result.get("mood", "informational")
            confidence = float(result.get("confidence", 0.5))
            if mood not in MOOD_DESCRIPTIONS:
                mood = "informational"
            return {"mood": mood, "confidence": confidence, "reason": result.get("reason", "")}
    except Exception:
        pass

    return _fallback_mood(text_to_analyze)


def _fallback_mood(text: str) -> dict:
    t = text.lower()
    breaking_words = ["breaking", "urgent", "emergency", "crisis", "disaster", "explosion", "attack", "war", "deadly", "critical"]
    sad_words = ["sad", "tragic", "death", "died", "mourn", "loss", "heartbreaking", "victim", "fatal", "grief"]
    inspirational_words = ["success", "achievement", "breakthrough", "victory", "celebrate", "inspiring", "hope", "milestone", "record", "triumph"]
    serious_words = ["political", "government", "court", "legal", "investigation", "official", "minister", "president", "policy", "security"]

    score_map = {"breaking": 0, "serious": 0, "sad": 0, "inspirational": 0, "informational": 0}

    for w in breaking_words:
        if w in t:
            score_map["breaking"] += 2
    for w in sad_words:
        if w in t:
            score_map["sad"] += 2
    for w in inspirational_words:
        if w in t:
            score_map["inspirational"] += 2
    for w in serious_words:
        if w in t:
            score_map["serious"] += 2

    max_mood = max(score_map, key=score_map.get)
    if score_map[max_mood] == 0:
        return {"mood": "informational", "confidence": 0.5, "reason": "neutral content"}
    return {"mood": max_mood, "confidence": 0.6 + (score_map[max_mood] * 0.05), "reason": f"keyword match: {max_mood}"}


def detect_mood(audio_path: str = None, topic: str = "") -> dict:
    transcript = transcribe_audio(audio_path) if audio_path else ""
    return analyze_mood_from_text(transcript, topic)


def extract_topic_from_audio(audio_path: str) -> dict:
    transcript = transcribe_audio(audio_path) if audio_path else ""
    if not transcript.strip():
        return {"topic": "general news", "language": "English", "full_transcript": ""}

    try:
        if OPENCODE_ZEN_API_KEY:
            from openai import OpenAI
            client = OpenAI(api_key=OPENCODE_ZEN_API_KEY, base_url=OPENCODE_ZEN_BASE_URL)
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": """You are a news analyzer.
Given a transcript (which may be in any Indian language like Marathi, Hindi, Gujarati, etc.):
1. Identify what language the transcript is in
2. Extract the main news topic in English (short, 3-8 words)
3. Summarize what the news is about in 1-2 English sentences

Respond with ONLY valid JSON:
{"language": "detected_language_name", "topic": "short_english_topic", "summary": "1-2 sentence summary in English"}"""},
                    {"role": "user", "content": f"Transcript:\n\n{transcript[:3000]}"}
                ],
                temperature=0.1,
                max_tokens=512,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.choices[0].message.content)
            supported_langs = {"english": "English", "hindi": "Hindi", "marathi": "Marathi", "gujarati": "Gujarati"}
            detected_lang = result.get("language", "English").lower().strip()
            lang = "English"
            for key, val in supported_langs.items():
                if key in detected_lang:
                    lang = val
                    break
            return {
                "topic": result.get("topic", "general news"),
                "language": lang,
                "summary": result.get("summary", ""),
                "full_transcript": transcript,
            }
    except Exception:
        pass

    return {"topic": "general news", "language": "English", "summary": "", "full_transcript": transcript}


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path:
        result = extract_topic_from_audio(path)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        topic = "test news"
        result = detect_mood(None, topic)
        print(json.dumps(result, indent=2))
