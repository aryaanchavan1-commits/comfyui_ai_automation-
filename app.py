import os
import sys
import json
import time
import html
import logging
from pathlib import Path

import streamlit as st
from streamlit.components.v1 import html as st_html

logger = logging.getLogger("sagarwave.app")

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    COMFYUI_URL, OUTPUT_DIR, SUPPORTED_LANGUAGES,
    REEL_DURATIONS, RESOLUTIONS, MOOD_THEMES, DEFAULT_MOOD,
)
from comfyui_automator import ComfyUIAutomator
from agent_core import AgentBrain
from pipeline_manager import PipelineManager
from model_manager import ModelManager, RECOMMENDED_MODELS
from emotion_analyzer import detect_mood

st.set_page_config(
    page_title="Sagarwave AI Agent",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "Sagarwave AI Agent – DeepSeek V4 Flash + ComfyUI"},
)

# ─── ROYAL DARK THEME ──────────────────────────────────────
st.markdown("""
<style>
    /* Royal Dark Theme */
    .stApp {
        background: #0a0e1a;
        color: #c8d6e5;
    }
    .stApp > header { background: #0a0e1a !important; }

    /* Headers */
    .main-header {
        text-align: center; padding: 1.2rem 0;
        background: linear-gradient(135deg, #0f1a3a, #1a0a2e);
        border-bottom: 2px solid #d4a017;
        margin-bottom: 1rem;
        border-radius: 0 0 12px 12px;
        box-shadow: 0 4px 20px rgba(212,160,23,0.15);
    }
    .main-header h1 {
        color: #d4a017; margin: 0; font-size: 2rem;
        text-shadow: 0 0 20px rgba(212,160,23,0.3);
    }
    .main-header p { color: #7a8ba8; margin: 0; font-size: 0.9rem; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0; background: #0f1525;
        border-radius: 10px; padding: 4px;
        border: 1px solid #1a2540;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent; color: #7a8ba8;
        border-radius: 8px; padding: 8px 18px;
        border: none; font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1a2a5a, #2a1a4a);
        color: #d4a017; font-weight: 700;
        box-shadow: 0 0 15px rgba(212,160,23,0.2);
    }
    .stTabs [data-baseweb="tab"]:hover { color: #d4a017; }

    /* Input fields */
    .stTextInput input, .stTextArea textarea,
    .stSelectbox, .stSlider, .stNumberInput {
        background: #0f1525 !important;
        border: 1px solid #1a2540 !important;
        color: #c8d6e5 !important;
        border-radius: 8px !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #d4a017 !important;
        box-shadow: 0 0 10px rgba(212,160,23,0.15) !important;
    }
    .stTextInput label, .stTextArea label,
    .stSelectbox label, .stSlider label {
        color: #7a8ba8 !important;
    }

    /* Buttons */
    .stButton button {
        background: linear-gradient(135deg, #1a2a5a, #2a1a4a);
        color: #d4a017; border: 1px solid #2a3a6a;
        border-radius: 8px; font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        background: linear-gradient(135deg, #2a3a7a, #3a2a5a);
        border-color: #d4a017; box-shadow: 0 0 20px rgba(212,160,23,0.3);
        transform: translateY(-1px);
    }
    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, #d4a017, #b8860b);
        color: #0a0e1a; border: none;
        font-weight: 700;
    }
    .stButton button[kind="primary"]:hover {
        background: linear-gradient(135deg, #e8b82a, #d4a017);
        box-shadow: 0 0 25px rgba(212,160,23,0.4);
    }

    /* File uploader */
    .stFileUploader {
        background: #0f1525 !important;
        border: 1px dashed #1a2540 !important;
        border-radius: 8px !important;
    }
    .stFileUploader:hover { border-color: #d4a017 !important; }

    /* Expanders */
    .stExpander {
        background: #0f1525 !important;
        border: 1px solid #1a2540 !important;
        border-radius: 8px !important;
    }
    .stExpander summary { color: #d4a017; font-weight: 600; }

    /* Progress bar */
    .stProgress > div > div { background: linear-gradient(90deg, #d4a017, #e8b82a) !important; }

    /* Chat messages */
    .chat-msg {
        padding: 1rem; border-radius: 10px; margin: 0.5rem 0;
    }
    .chat-user {
        background: linear-gradient(135deg, #0f1a3a, #15102a);
        border-left: 3px solid #4a7aff;
    }
    .chat-agent {
        background: linear-gradient(135deg, #1a0a2e, #1a1510);
        border-left: 3px solid #d4a017;
    }

    /* Status boxes */
    .status-box {
        padding: 0.8rem; border-radius: 8px; margin: 0.5rem 0;
        text-align: center; font-weight: 600;
    }
    .status-running { background: #0a1a1a; border: 1px solid #00cc88; color: #00cc88; }
    .status-done { background: #0a1a0a; border: 1px solid #66ff66; color: #66ff66; }
    .status-error { background: #1a0a0a; border: 1px solid #ff4444; color: #ff4444; }
    .status-idle { background: #0f1525; border: 1px solid #7a8ba8; color: #7a8ba8; }

    /* Cards */
    .card {
        background: #0f1525; border: 1px solid #1a2540;
        border-radius: 10px; padding: 1rem; margin: 0.5rem 0;
    }
    .card:hover { border-color: #d4a017; transition: 0.3s; }

    /* Voice button */
    .voice-btn {
        background: linear-gradient(135deg, #1a2a5a, #2a1a4a);
        color: #d4a017; border: 2px solid #2a3a6a;
        border-radius: 50%; width: 48px; height: 48px;
        font-size: 1.4rem; cursor: pointer;
        display: inline-flex; align-items: center;
        justify-content: center; transition: all 0.3s;
    }
    .voice-btn:hover { border-color: #d4a017; box-shadow: 0 0 20px rgba(212,160,23,0.3); }
    .voice-btn.recording {
        background: linear-gradient(135deg, #5a1a1a, #4a0a0a);
        border-color: #ff4444; color: #ff4444;
        animation: pulse 1s infinite;
    }
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(255,68,68,0.4); }
        70% { box-shadow: 0 0 0 10px rgba(255,68,68,0); }
        100% { box-shadow: 0 0 0 0 rgba(255,68,68,0); }
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #0a0e1a !important;
        border-right: 1px solid #1a2540 !important;
    }
    section[data-testid="stSidebar"] .stMarkdown {
        color: #7a8ba8;
    }

    /* Metric cards */
    [data-testid="stMetricValue"] {
        color: #d4a017 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #7a8ba8 !important;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0a0e1a; }
    ::-webkit-scrollbar-thumb { background: #1a2540; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #2a3a6a; }

    /* Info/Success/Error/Warning boxes */
    .stAlert { background: #0f1525 !important; border: 1px solid #1a2540 !important; }
    .stAlert [data-testid="stMarkdownContainer"] { color: #c8d6e5 !important; }

    /* Help tab styling */
    .help-step {
        background: #0f1525; border: 1px solid #1a2540;
        border-radius: 10px; padding: 1.2rem; margin: 0.8rem 0;
        border-left: 3px solid #d4a017;
    }
    .help-step h4 { color: #d4a017; margin: 0 0 0.5rem 0; }
    .help-step p { color: #9aabbe; margin: 0; }

    .feature-card {
        background: linear-gradient(135deg, #0f1a3a, #1a0a2e);
        border: 1px solid #1a2540; border-radius: 10px;
        padding: 1rem; text-align: center;
    }
    .feature-card h3 { color: #d4a017; margin: 0.5rem 0; }
    .feature-card p { color: #7a8ba8; font-size: 0.85rem; margin: 0; }
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="main-header">'
    '<h1>👑 Sagarwave AI Agent</h1>'
    '<p>DeepSeek V4 Flash · ComfyUI Automation · Multi-Language News Studio</p>'
    '</div>',
    unsafe_allow_html=True,
)

# ─── Voice Recognition Component ────────────────────────
VOICE_HTML = """
<div style="text-align:center; padding:0.5rem;">
    <button id="voiceBtn" class="voice-btn" onclick="toggleRecording()">🎤</button>
    <p id="voiceStatus" style="color:#7a8ba8;font-size:0.8rem;margin:0.3rem 0;">Click to speak</p>
</div>
<script>
let recognizing = false;
let recognition = null;
if ('webkitSpeechRecognition' in window) {
    recognition = new webkitSpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    recognition.onstart = function() {
        recognizing = true;
        document.getElementById('voiceBtn').classList.add('recording');
        document.getElementById('voiceStatus').textContent = '🎙️ Listening...';
    };
    recognition.onend = function() {
        recognizing = false;
        document.getElementById('voiceBtn').classList.remove('recording');
        document.getElementById('voiceStatus').textContent = 'Click to speak';
    };
    recognition.onerror = function(event) {
        recognizing = false;
        document.getElementById('voiceBtn').classList.remove('recording');
        document.getElementById('voiceStatus').textContent = 'Error: ' + event.error;
        setTimeout(() => document.getElementById('voiceStatus').textContent = 'Click to speak', 2000);
    };
    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        document.getElementById('voiceStatus').textContent = '✅ "' + transcript + '"';
        const input = document.createElement('input');
        input.id = 'voiceResult';
        input.value = transcript;
        document.body.appendChild(input);
        input.dispatchEvent(new Event('change', {bubbles: true}));
        setTimeout(() => {
            if (document.getElementById('voiceResult')) document.getElementById('voiceResult').remove();
        }, 100);
    };
} else {
    document.getElementById('voiceStatus').textContent = '❌ Voice not supported in this browser';
}
function toggleRecording() {
    if (!recognition) return;
    if (recognizing) { recognition.stop(); return; }
    recognition.start();
}
</script>
"""

# ─── Initialize ────────────────────────────────────────────
if "comfy" not in st.session_state:
    st.session_state.comfy = ComfyUIAutomator(COMFYUI_URL)
if "brain" not in st.session_state:
    st.session_state.brain = AgentBrain()
if "pipeline" not in st.session_state:
    st.session_state.pipeline = PipelineManager(
        st.session_state.comfy, st.session_state.brain
    )
if "model_manager" not in st.session_state:
    st.session_state.model_manager = ModelManager(st.session_state.comfy)
if "detected_mood" not in st.session_state:
    st.session_state.detected_mood = DEFAULT_MOOD
if "mood_confidence" not in st.session_state:
    st.session_state.mood_confidence = 0.0
if "mood_reason" not in st.session_state:
    st.session_state.mood_reason = ""
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pipeline_events" not in st.session_state:
    st.session_state.pipeline_events = []
if "output_files" not in st.session_state:
    st.session_state.output_files = []
if "voice_text" not in st.session_state:
    st.session_state.voice_text = ""

comfy = st.session_state.comfy
brain = st.session_state.brain
pipeline = st.session_state.pipeline
model_mgr = st.session_state.model_manager

# ─── Detect voice result ──────────────────────────────────
# (handled via rerun trigger in the voice section below)

# ─── Sidebar ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 👑 Sagarwave AI")
    st.markdown("---")

    comfy_online = comfy.is_online()
    brain_online = brain.available()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("ComfyUI", "✅ ON" if comfy_online else "❌ OFF")
    with col2:
        st.metric("AI Brain", "✅ ON" if brain_online else "⚠️ FALLBACK")

    if comfy_online:
        try:
            stats = comfy.get_system_stats()
            dev = stats.get("system", {}).get("devices", [{}])[0]
            st.caption(f"🎮 {dev.get('name', 'GPU')} · "
                       f"{dev.get('vram_total', 0)/1e9:.1f}GB VRAM")
        except Exception as e:
            logger.debug("Could not fetch GPU stats: %s", e)
    else:
        st.info("Start ComfyUI Desktop then refresh")

    st.markdown("---")
    st.markdown("### 📋 Pipeline")
    state = pipeline.get_state()
    p_status = state["status"]
    status_cls = {"running": "status-running", "completed": "status-done",
                  "failed": "status-error"}.get(p_status, "status-idle")
    status_icon = {"running": "⏳", "completed": "✅", "failed": "❌"}.get(p_status, "💤")
    st.markdown(
        f'<div class="status-box {status_cls}">'
        f'{status_icon} {p_status.title()}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("### 📁 Uploads")

    anchor_img = st.file_uploader(
        "🧑 Anchor Image", type=["jpg", "jpeg", "png"],
        key="sidebar_anchor",
    )
    voice_file = st.file_uploader(
        "🎤 Voice Audio", type=["wav", "mp3", "m4a"],
        key="sidebar_voice",
    )
    news_imgs = st.file_uploader(
        "🖼️ News Visuals", type=["jpg", "jpeg", "png"],
        accept_multiple_files=True, key="sidebar_visuals",
    )

    st.markdown("---")
    st.markdown('<div class="card" style="text-align:center;">', unsafe_allow_html=True)
    st_html(VOICE_HTML, height=90)
    st.caption("🎤 Mic works from any tab")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    if st.button("🗑️ Clear Session", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pipeline_events = []
        brain.clear_history()
        st.rerun()


def _fast_chat(query: str) -> str:
    if brain.available():
        try:
            resp = brain.client.chat.completions.create(
                model="deepseek-v4-flash-free",
                messages=[
                    {"role": "system",
                     "content": "You are Sagarwave AI, a helpful assistant for "
                                "a news studio app. Answer concisely and practically. "
                                "NO JSON. NO markdown code blocks."},
                    {"role": "user", "content": query}
                ],
                temperature=0.3,
                max_tokens=1024,
            )
            return resp.choices[0].message.content
        except Exception as e:
            logger.warning("Fast chat failed: %s", e)
    return _fallback_help_answer(query)


def _fallback_help_answer(query: str) -> str:
    q = query.lower()
    if "language" in q or "hindi" in q or "marathi" in q or "gujarati" in q:
        return "Supported languages: English, Hindi, Marathi, Gujarati. Select your language in the News Studio form or mention it in AI Chat."
    if "upload" in q or "image" in q or "photo" in q:
        return "Upload assets in the sidebar (left panel): Anchor Image, Voice Audio, and News Visuals. Supported formats: PNG, JPG, WAV, MP3."
    if "how long" in q or "time" in q or "duration" in q:
        return "Generation takes 1-5 minutes depending on video length. A 30-second reel is ~1-2 min, a 5-minute video may take 4-5 min."
    if "fail" in q or "error" in q or "not working" in q or "bug" in q:
        return "First, ensure ComfyUI Desktop is running at http://127.0.0.1:8188. Then check the console for error details. Common fixes: restart ComfyUI, free up VRAM, or reduce video duration."
    if "avatar" in q or "anchor" in q or "talking" in q:
        return "Upload a clear front-facing photo in the sidebar under Anchor Image. The system uses LivePortrait to animate it with lip-sync. Best results with well-lit, straight-on portraits."
    if "tutorial" in q or "guide" in q or "how to" in q or "help" in q:
        return "Quick start: (1) Go to News Studio tab, (2) Enter topic + language + duration, (3) Upload anchor photo in sidebar, (4) Click Generate News Reel, (5) Find output in the Outputs tab."
    if "comfyui" in q or "install" in q or "model" in q:
        return "ComfyUI Desktop must be running separately. The agent connects to it at http://127.0.0.1:8188. Make sure required models (SDXL, LivePortrait) are installed in ComfyUI."
    return (f"Regarding '{query}' — this AI news studio generates professional multi-language "
            "news reels with talking avatars. Use the News Studio tab to create videos, "
            "AI Chat for natural language requests, Workflows for custom ComfyUI pipelines, "
            "and Outputs to view/download results.")


# ─── Main Tabs ─────────────────────────────────────────────
tab_chat, tab_news, tab_i2v, tab_workflow, tab_outputs = st.tabs([
    "💬 AI Chat & Help", "📰 News Studio", "🎬 I2V Studio", "⚙️ Workflows", "📁 Outputs"
])

# ═══════════════════════════════════════════════════════════
# TAB 1: AI CHAT & HELP (merged)
# ═══════════════════════════════════════════════════════════
with tab_chat:
    st.subheader("💬 AI Chat & Help")

    if "help_messages" not in st.session_state:
        st.session_state.help_messages = [
            {"role": "assistant", "content":
             "Hi! I'm Sagarwave AI. Ask me anything about using this news "
             "studio, or just chat naturally. I respond fast!"}
        ]

    # Voice + chat input row
    vc1, vc2 = st.columns([1, 5])
    with vc1:
        st.markdown(
            '<div class="card" style="padding:0.3rem;text-align:center;">',
            unsafe_allow_html=True,
        )
        st_html(VOICE_HTML, height=90)
        st.markdown("</div>", unsafe_allow_html=True)
    with vc2:
        query = st.chat_input("Ask anything — chat, help, or news commands...")
        if query:
            st.session_state.help_messages.append(
                {"role": "user", "content": query}
            )
            with st.spinner("Thinking..."):
                answer = _fast_chat(query)
            st.session_state.help_messages.append(
                {"role": "assistant", "content": answer}
            )
            st.rerun()

    # Conversation display
    for msg in st.session_state.help_messages[-50:]:
        role = msg["role"]
        content = msg["content"]
        if role == "user":
            st.markdown(
                f'<div style="text-align:right;margin:1rem 0;">'
                f'<div style="font-size:0.8rem;color:#8899bb;margin-bottom:0.2rem;">You</div>'
                f'<span style="background:#1a3a6a;color:#ffffff;padding:0.9rem 1.3rem;'
                f'font-size:1.15rem;font-weight:500;line-height:1.5;'
                f'border-radius:16px 16px 4px 16px;display:inline-block;max-width:85%;'
                f'border:1px solid #d4a01777;">{html.escape(content)}</span></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="margin:1rem 0;">'
                f'<div style="font-size:0.8rem;color:#d4a017;margin-bottom:0.2rem;">Sagarwave AI</div>'
                f'<span style="background:#0d1b2a;color:#e8e8e8;padding:0.9rem 1.3rem;'
                f'font-size:1.1rem;line-height:1.6;'
                f'border-radius:16px 16px 16px 4px;display:inline-block;max-width:85%;'
                f'border:1px solid #d4a01755;">{content}</span></div>',
                unsafe_allow_html=True,
            )

    col_clr, _ = st.columns([1, 5])
    with col_clr:
        if st.button("🗑️ Clear All", use_container_width=True):
            st.session_state.help_messages = [
                {"role": "assistant",
                 "content": "Conversation cleared. Ask me anything!"}
            ]
            st.rerun()

    with st.expander("💡 Quick Help Topics", expanded=False):
        st.markdown("""
        - **Create a news video** — Go to **News Studio** tab, enter topic, language, click Generate
        - **Use voice** — Click 🎤 mic button (sidebar or above) and speak naturally
        - **Upload images** — Use sidebar: Anchor Image, Voice Audio, News Visuals
        - **Languages** — English, Hindi, Marathi, Gujarati
        - **Troubleshooting** — Make sure ComfyUI Desktop is running on port 8188
        """)

# ═══════════════════════════════════════════════════════════
# TAB 2: NEWS STUDIO
# ═══════════════════════════════════════════════════════════
with tab_news:
    col_setup, col_preview = st.columns([5, 4])

    with col_setup:
        st.subheader("📰 Generate News Reel")

        with st.expander("📝 News Script", expanded=True):
            topic = st.text_input(
                "News Topic",
                placeholder="e.g., Maharashtra farmers protest, technology breakthrough...",
                key="news_topic",
            )

            col_l, col_d = st.columns(2)
            with col_l:
                lang = st.selectbox(
                    "🌐 Language", list(SUPPORTED_LANGUAGES.keys()),
                    key="news_lang",
                )
            with col_d:
                dur_label = st.selectbox(
                    "⏱️ Duration", list(REEL_DURATIONS.keys()),
                    key="news_dur",
                )
                dur_min, dur_max = REEL_DURATIONS[dur_label]
                duration = st.slider(
                    "Seconds", dur_min, dur_max,
                    min(dur_min + 15, dur_max),
                    key="news_sec",
                )

            tone = st.selectbox(
                "🎭 Tone",
                ["professional", "casual", "urgent", "inspirational"],
                key="news_tone",
            )

        with st.expander("🎭 Avatar & Audio", expanded=False):
            if anchor_img:
                st.image(anchor_img, width=120)
                st.caption(f"Anchor: {anchor_img.name}")
            else:
                st.info("Upload an anchor image in sidebar")
            if voice_file:
                st.audio(voice_file)
                st.caption(f"Voice: {voice_file.name}")

        with st.expander("🎭 AI Mood Detection", expanded=False):
            st.caption("Auto-detects emotion from uploaded voice / topic and adjusts visuals accordingly")
            mood_options = {v["name"]: k for k, v in MOOD_THEMES.items()}
            detected = st.session_state.detected_mood
            mood_name = MOOD_THEMES.get(detected, MOOD_THEMES[DEFAULT_MOOD])["name"]
            confidence = st.session_state.mood_confidence
            reason = st.session_state.mood_reason
            if confidence > 0:
                st.success(f"🎯 **Detected:** {mood_name} ({confidence:.0%} confidence)")
                if reason:
                    st.caption(f"Reason: {reason}")
            mood_override = st.selectbox(
                "Manual override (optional)", list(mood_options.keys()),
                index=list(mood_options.values()).index(detected) if detected in mood_options.values() else 0,
                key="mood_override",
            )
            st.session_state.override_mood = mood_options[mood_override]

        with st.expander("🖼️ Visuals & Output", expanded=False):
            resolution_label = st.selectbox(
                "📐 Resolution", list(RESOLUTIONS.keys()),
                key="news_res",
            )

            if news_imgs:
                st.success(f"{len(news_imgs)} visual(s) ready")
            else:
                st.info("Upload news visuals in sidebar (optional)")

        gen_btn = st.button(
            "🚀 Generate News Reel", type="primary",
            use_container_width=True, disabled=not topic or not comfy_online,
        )

        if gen_btn:
            event_holder = st.empty()
            progress_bar = st.progress(0, text="Starting...")

            save_imgs = []
            if anchor_img:
                ap = OUTPUT_DIR / "uploads" / anchor_img.name
                ap.parent.mkdir(exist_ok=True)
                with open(ap, "wb") as f:
                    f.write(anchor_img.getbuffer())
                save_imgs.append(str(ap))

            voice_path = None
            if voice_file:
                vp = OUTPUT_DIR / "uploads" / voice_file.name
                vp.parent.mkdir(exist_ok=True)
                with open(vp, "wb") as f:
                    f.write(voice_file.getbuffer())
                voice_path = str(vp)

            extra_imgs = []
            if news_imgs:
                for ni in news_imgs:
                    nip = OUTPUT_DIR / "uploads" / ni.name
                    nip.parent.mkdir(exist_ok=True)
                    with open(nip, "wb") as f:
                        f.write(ni.getbuffer())
                    extra_imgs.append(str(nip))

            # Detect mood from voice or topic
            with st.spinner("🎯 Analyzing emotion from audio..."):
                mood_result = detect_mood(voice_path, topic)
                st.session_state.detected_mood = mood_result.get("mood", DEFAULT_MOOD)
                st.session_state.mood_confidence = mood_result.get("confidence", 0.0)
                st.session_state.mood_reason = mood_result.get("reason", "")
                event_holder.info(f"🎭 Detected mood: {MOOD_THEMES.get(st.session_state.detected_mood, MOOD_THEMES[DEFAULT_MOOD])['name']}")

            mood_to_use = st.session_state.get("override_mood") or st.session_state.detected_mood
            pipeline.set_mood(mood_to_use)

            def on_progress(event):
                if event["type"] == "pipeline":
                    total = event["total"]
                    step = event["step"]
                    if total > 0:
                        progress_bar.progress(step / total, text=event["text"])
                        event_holder.info(
                            f"Step {step}/{total}: {event['text']}"
                        )
                    else:
                        event_holder.error(event["text"])
                elif event["type"] == "progress":
                    event_holder.info(event.get("text", ""))
                elif event["type"] == "error":
                    event_holder.error(event.get("text", ""))
                elif event["type"] == "complete":
                    progress_bar.progress(1.0, text="✅ Done!")

            result = pipeline.execute_news_pipeline(
                topic=topic, language=lang, duration=duration,
                anchor_image=save_imgs[0] if save_imgs else None,
                voice_audio=voice_path,
                news_images=extra_imgs if extra_imgs else None,
                mood=mood_to_use,
                progress_callback=on_progress,
            )

            if result["status"] == "completed":
                st.balloons()
                st.success("✅ News reel generated!")
                for out in result.get("outputs", []):
                    st.session_state.output_files.append(out)
                    st.video(out)
            else:
                st.error(f"❌ {result.get('error', 'Generation failed')}")

    with col_preview:
        st.subheader("🔮 Pipeline Overview")
        steps = [
            ("📝", "Script", "AI writes news script in your language"),
            ("🎤", "TTS Voice", "edge-tts converts to natural speech"),
            ("🖼️", "Visuals", "Generate or use uploaded news images"),
            ("🎭", "Avatar", "Talking head with lip sync animation"),
            ("🎬", "Compose", "Final video with subtitles & branding"),
        ]
        for icon, name, desc in steps:
            st.markdown(
                f'<div class="card">'
                f'<strong>{icon} {name}</strong><br>'
                f'<span style="color:#7a8ba8;font-size:0.85rem;">{desc}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.divider()
        st.markdown("**💡 Tips**")
        st.caption("• Upload a clear front-facing anchor photo")
        st.caption("• Use short, impactful news topics")
        st.caption("• For best lip sync, keep videos under 3 min")

# ═══════════════════════════════════════════════════════════
# TAB 3: I2V STUDIO
# ═══════════════════════════════════════════════════════════
with tab_i2v:
    st.subheader("🎬 Image + Audio to Professional Video")
    st.caption("Upload any image and voice audio — generates a professional news-style video with animated talking head, subtitles, and broadcast graphics. Now with Ken Burns effect and AnimateDiff-ready background animation.")

    col_i2v_left, col_i2v_right = st.columns([5, 4])

    with col_i2v_left:
        i2v_image = st.file_uploader(
            "🖼️ Upload Image (face/portrait)", type=["jpg", "jpeg", "png"],
            key="i2v_image",
        )
        i2v_audio = st.file_uploader(
            "🎤 Upload Voice Audio", type=["wav", "mp3", "m4a", "ogg"],
            key="i2v_audio",
        )
        i2v_topic = st.text_input(
            "📰 News Topic (for headline/ticker)",
            placeholder="e.g., Breaking news in technology...",
            key="i2v_topic",
        )

        i2v_lang = st.selectbox(
            "🌐 Language", list(SUPPORTED_LANGUAGES.keys()),
            key="i2v_lang",
        )

        if i2v_audio:
            st.audio(i2v_audio)

        i2v_ready = i2v_image is not None and i2v_audio is not None and comfy_online
        i2v_gen_btn = st.button(
            "🚀 Generate Professional Video", type="primary",
            use_container_width=True, disabled=not i2v_ready,
        )

        if i2v_gen_btn:
            event_holder = st.empty()
            progress_bar = st.progress(0, text="Starting...")

            save_img = OUTPUT_DIR / "uploads" / i2v_image.name
            save_img.parent.mkdir(exist_ok=True)
            with open(save_img, "wb") as f:
                f.write(i2v_image.getbuffer())

            save_audio = OUTPUT_DIR / "uploads" / i2v_audio.name
            with open(save_audio, "wb") as f:
                f.write(i2v_audio.getbuffer())

            # Detect mood
            with st.spinner("Analyzing emotion from audio..."):
                mood_result = detect_mood(str(save_audio), i2v_topic)
                detected = mood_result.get("mood", DEFAULT_MOOD)
                st.session_state.detected_mood = detected
                st.session_state.mood_confidence = mood_result.get("confidence", 0.0)
                event_holder.info(f"Detected mood: {MOOD_THEMES.get(detected, MOOD_THEMES[DEFAULT_MOOD])['name']}")

            pipeline.set_mood(detected)

            def i2v_progress(event):
                if event["type"] == "pipeline":
                    total = event["total"]
                    step = event["step"]
                    if total > 0:
                        progress_bar.progress(step / total, text=event["text"])
                        event_holder.info(f"Step {step}/{total}: {event['text']}")
                    else:
                        event_holder.error(event["text"])
                elif event["type"] == "progress":
                    event_holder.info(event.get("text", ""))
                elif event["type"] == "error":
                    event_holder.error(event.get("text", ""))
                elif event["type"] == "complete":
                    progress_bar.progress(1.0, text="Done!")

            result = pipeline.generate_i2v_video(
                image_path=str(save_img),
                audio_path=str(save_audio),
                topic=i2v_topic or "News Update",
                mood=detected,
                progress_callback=i2v_progress,
            )

            if result["status"] == "completed":
                st.balloons()
                st.success("Professional video generated!")
                for out in result.get("outputs", []):
                    st.session_state.output_files.append(out)
                    st.video(out)
            else:
                st.error(f"Failed: {result.get('error', 'Unknown error')}")

    with col_i2v_right:
        st.markdown("### 🔮 Pipeline Steps")
        steps_i2v = [
            ("🖼️", "Upload Image", "Your image becomes the talking avatar"),
            ("🎤", "Voice Sync", "Audio drives lip-sync animation"),
            ("🎭", "LivePortrait", "Realistic talking head generation"),
            ("🎬", "Compose", "Ken Burns zoom + broadcast graphics + subtitles"),
            ("📦", "Output", "Professional MP4 ready to share"),
        ]
        for icon, name, desc in steps_i2v:
            st.markdown(
                f'<div class="card" style="padding:0.7rem;">'
                f'<strong>{icon} {name}</strong><br>'
                f'<span style="color:#7a8ba8;font-size:0.85rem;">{desc}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.divider()
        st.markdown("**🎯 Tips**")
        st.caption("• Use a clear front-facing photo for best lip-sync")
        st.caption("• Audio should be clear speech (any language)")
        st.caption("• For AnimateDiff animated backgrounds, use Workflows tab")
        st.caption("• LivePortrait + Realistic Vision + Ken Burns zoom = professional quality")

# ═══════════════════════════════════════════════════════════
# TAB 4: WORKFLOW + MODELS
# ═══════════════════════════════════════════════════════════
with tab_workflow:
    wf_tabs = st.tabs(["⚡ Smart Run", "🔧 Manual", "📦 Models", "🔍 Nodes"])

    # ─── Smart Run ──────────────────────────────────────
    with wf_tabs[0]:
        st.subheader("⚡ Autonomous AI Agent")
        st.caption("I discover nodes, build workflows, download missing models, and run everything for you.")

        smart_prompt = st.text_area(
            "Describe what you want to generate:",
            placeholder="e.g., Generate a 1024x1024 image of a futuristic city with Flux model, "
                        "or Create a talking avatar video from this image with lip sync, "
                        "or Upscale this image 4x with a realistic model, "
                        "or ControlNet canny of this image with a prompt",
            height=100,
            key="smart_prompt",
        )

        auto_mode = st.radio("Execution Mode",
                              ["Generate Workflow Only", "Full Auto (Discover → Build → Download → Run)"],
                              horizontal=True, index=1)

        col_check, col_auto = st.columns(2)
        with col_check:
            check_nodes = st.button("🔍 Check Available Nodes", use_container_width=True)
        with col_auto:
            auto_btn = st.button("🤖 Do Everything For Me", type="primary",
                                 use_container_width=True,
                                 disabled=not smart_prompt or not comfy_online)

        if check_nodes and comfy_online:
            with st.spinner("Discovering ComfyUI nodes..."):
                try:
                    node_info = comfy.get_object_info()
                    nodes = sorted(node_info.keys())
                    st.success(f"Found {len(nodes)} available nodes")
                    brain.cache_nodes(node_info)
                    with st.expander(f"📋 All {len(nodes)} Nodes", expanded=False):
                        cols = st.columns(3)
                        for i, n in enumerate(nodes):
                            cols[i % 3].code(n, language="")
                except Exception as e:
                    st.error(f"Node discovery failed: {e}")

        if auto_btn and smart_prompt and comfy_online:
            status_area = st.empty()
            progress_bar = st.progress(0, text="Starting...")
            output_area = st.container()

            def auto_callback(event):
                if event["type"] == "progress":
                    progress_bar.progress(
                        min(event.get("percent", 50) / 100, 0.95),
                        text=event.get("text", "")
                    )
                elif event["type"] == "status":
                    progress_bar.progress(event.get("percent", 0.5),
                                          text=event.get("text", ""))
                    status_area.info(event.get("text", ""))

            with st.status("🤖 Autonomous Agent Working...", expanded=True) as status:
                try:
                    node_info = comfy.get_object_info()
                    brain.cache_nodes(node_info)
                    available_nodes = sorted(node_info.keys())
                    status.write(f"✅ **Discovered** {len(available_nodes)} nodes")

                    wf_result = brain.execute_autonomous(
                        smart_prompt, comfy, model_mgr
                    )
                    workflow = wf_result.get("workflow", {})
                    exec_steps = wf_result.get("steps", [])
                    errors = wf_result.get("errors", [])

                    for s in exec_steps:
                        icon = "✅" if s["status"] == "done" else "⚠️" if s["status"] == "warning" else "❌"
                        status.write(f"{icon} **{s['step']}** — {s['status']}")

                    if not workflow:
                        status.error("❌ No workflow generated")
                        st.stop()

                    if errors:
                        for e in errors:
                            status.warning(f"⚠️ {e}")

                    status.write("✅ **Workflow generated successfully**")
                    with st.expander("📋 Workflow JSON", expanded=False):
                        st.json(workflow)

                    if auto_mode == "Full Auto (Discover → Build → Download → Run)":
                        status.write("🚀 **Running workflow in ComfyUI...**")
                        result = comfy.execute_pipeline(workflow, wait=True)

                        if result["status"] == "completed":
                            status.success("✅ **Workflow completed!**")
                            output_files = result.get("output_files", [])
                            for f in output_files:
                                try:
                                    data = comfy.download_output(f)
                                    st.download_button(f"⬇️ {f}", data, file_name=f)
                                except Exception as ex:
                                    logger.debug("Could not download output %s: %s", f, ex)
                                    st.info(f"Output generated: {f}")
                        else:
                            status.error("❌ Workflow execution failed")

                except Exception as e:
                    status.error(f"❌ Autonomous execution failed: {e}")

    # ─── Manual ─────────────────────────────────────────
    with wf_tabs[1]:
        st.subheader("🔧 Manual Workflow Runner")
        wf_dir = Path("workflow_templates")
        wf_dir.mkdir(exist_ok=True)
        wf_files = list(wf_dir.glob("*.json"))

        col_wf_list, col_wf_detail = st.columns([1, 2])
        with col_wf_list:
            if wf_files:
                selected_wf = st.selectbox(
                    "Saved Workflows", [wf.name for wf in wf_files],
                    key="manual_wf_select"
                )
                if selected_wf:
                    with open(wf_dir / selected_wf) as f:
                        st.json(json.load(f))
            else:
                st.info("No saved workflows yet")

            with st.expander("💾 Save Current"):
                wf_name_save = st.text_input("Name:", key="wf_save_name")
                wf_json_save = st.text_area("JSON:", height=150, key="wf_save_json")
                if st.button("Save", key="wf_save_btn") and wf_name_save and wf_json_save:
                    try:
                        data = json.loads(wf_json_save)
                        with open(wf_dir / f"{wf_name_save}.json", "w") as f:
                            json.dump(data, f, indent=2)
                        st.success("Saved!")
                    except json.JSONDecodeError:
                        st.error("Invalid JSON")

        with col_wf_detail:
            run_options = ["T2I (SDXL)", "T2I (Flux)", "Talking Head"] + \
                          [wf.name for wf in wf_files]
            run_wf = st.selectbox("Select Workflow", run_options, key="manual_wf_run")
            prompt = st.text_area("Prompt", placeholder="Describe what to generate...",
                                  height=80, key="manual_prompt")
            col_s, col_c = st.columns(2)
            with col_s:
                steps = st.number_input("Steps", 1, 100, 20, key="manual_steps")
            with col_c:
                cfg = st.number_input("CFG", 1.0, 20.0, 7.0, 0.5, key="manual_cfg")

            if st.button("▶️ Run Now", type="primary", use_container_width=True,
                         disabled=not comfy_online):
                with st.spinner("Running in ComfyUI..."):
                    if run_wf.endswith(".json"):
                        workflow = comfy.load_workflow(str(wf_dir / run_wf))
                    else:
                        workflow = {
                            "3": {"class_type": "KSampler",
                                  "inputs": {"seed": int(time.time()),
                                             "steps": steps, "cfg": cfg,
                                             "sampler_name": "euler",
                                             "scheduler": "normal",
                                             "denoise": 1.0,
                                             "model": ["4", 0],
                                             "positive": ["6", 0],
                                             "negative": ["7", 0],
                                             "latent_image": ["5", 0]}},
                            "4": {"class_type": "CheckpointLoaderSimple",
                                  "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}},
                            "5": {"class_type": "EmptyLatentImage",
                                  "inputs": {"width": 1024, "height": 1024,
                                             "batch_size": 1}},
                            "6": {"class_type": "CLIPTextEncode",
                                  "inputs": {"text": prompt, "clip": ["4", 1]}},
                            "7": {"class_type": "CLIPTextEncode",
                                  "inputs": {"text": "bad quality, blurry",
                                             "clip": ["4", 1]}},
                            "8": {"class_type": "VAEDecode",
                                  "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
                            "9": {"class_type": "SaveImage",
                                  "inputs": {"filename_prefix": "agent_output",
                                             "images": ["8", 0]}},
                        }
                    result = comfy.execute_pipeline(workflow, wait=True)
                    if result["status"] == "completed":
                        st.success("✅ Workflow done!")
                        for f in result.get("output_files", []):
                            try:
                                data = comfy.download_output(f)
                                st.download_button(f"⬇️ {f}", data, file_name=f)
                            except Exception:
                                st.info(f"Output: {f}")
                    else:
                        st.error("Workflow failed")

    # ─── Models ─────────────────────────────────────────
    with wf_tabs[2]:
        st.subheader("📦 Model Manager")
        st.caption("Download models directly into ComfyUI from HuggingFace or CivitAI")

        if comfy_online:
            with st.spinner("Scanning installed models..."):
                all_models = model_mgr.scan_installed_models()
            if all_models:
                for folder, models in list(all_models.items())[:6]:
                    with st.expander(f"{folder} ({len(models)} models)", expanded=False):
                        for m in models[:20]:
                            st.code(m, language="")
                        if len(models) > 20:
                            st.caption(f"... and {len(models)-20} more")
            else:
                st.info("No models detected or ComfyUI folder API unavailable")

            st.divider()
            st.markdown("### ⬇️ Download Model")

            dl_source = st.radio("Source", ["Quick Pick", "HuggingFace URL", "CivitAI URL"],
                                 horizontal=True)

            if dl_source == "Quick Pick":
                model_folder = st.selectbox(
                    "Model Type",
                    ["checkpoints", "loras", "vae", "controlnet", "upscale_models",
                     "clip", "clip_vision", "ipadapter"],
                    key="dl_folder"
                )
                quick_options = list(RECOMMENDED_MODELS.get(model_folder, {}).keys())
                if quick_options:
                    selected_model = st.selectbox("Select Model", quick_options)
                    dl_url = RECOMMENDED_MODELS[model_folder][selected_model]
                    st.code(dl_url, language="")
                    if st.button("⬇️ Download Selected Model", type="primary",
                                 use_container_width=True):
                        with st.spinner(f"Downloading {selected_model}..."):
                            result = model_mgr.download_if_missing(
                                selected_model, model_folder, dl_url
                            )
                            if result:
                                st.success(f"Downloaded to {result}")
                            else:
                                st.info("Already installed!")
                else:
                    st.info("No quick picks for this folder type")

            else:
                dl_url_input = st.text_input(
                    "Model URL",
                    placeholder="https://huggingface.co/... or https://civitai.com/...",
                    key="dl_url_input"
                )
                dl_folder = st.selectbox(
                    "Target Folder",
                    ["checkpoints", "loras", "vae", "controlnet", "upscale_models",
                     "clip", "clip_vision", "ipadapter"],
                    key="dl_folder_custom"
                )
                dl_name = st.text_input("Filename (optional, leave empty to auto-detect)",
                                        placeholder="model.safetensors")
                if st.button("⬇️ Download", type="primary",
                             use_container_width=True, disabled=not dl_url_input):
                    with st.spinner("Downloading..."):
                        try:
                            path = comfy.download_model(
                                dl_url_input, dl_folder,
                                filename=dl_name if dl_name else None
                            )
                            st.success(f"Downloaded to {path}")
                        except Exception as e:
                            st.error(f"Download failed: {e}")

            st.divider()
            st.markdown("### 🤖 Auto-Install from Request")
            auto_req = st.text_input(
                "Describe what you need:",
                placeholder="e.g., I need Flux for image generation, or Download a realistic model and a vae",
                key="auto_model_req"
            )
            if st.button("Auto-Install", type="primary",
                         use_container_width=True, disabled=not auto_req):
                with st.spinner("Checking and downloading required models..."):
                    results = model_mgr.auto_ensure_model(auto_req)
                    for r in results:
                        if r["action"] == "downloaded":
                            st.success(f"✅ Downloaded {r['name']} → {r['folder']}")
                        else:
                            st.info(f"✓ {r['name']} already installed in {r['folder']}")
        else:
            st.warning("ComfyUI is offline. Start it to manage models.")

    # ─── Nodes ──────────────────────────────────────────
    with wf_tabs[3]:
        st.subheader("🔍 ComfyUI Node Explorer")
        st.caption("Browse all available nodes and their inputs/outputs")

        if comfy_online:
            with st.spinner("Fetching node information..."):
                try:
                    node_info = comfy.get_object_info()
                    node_types = sorted(node_info.keys())

                    search = st.text_input("Search nodes:", placeholder="Type to filter...",
                                           key="node_search")
                    filtered = [n for n in node_types
                                if not search or search.lower() in n.lower()]

                    st.caption(f"Showing {len(filtered)} of {len(node_types)} nodes")

                    selected_node = st.selectbox("Select a node", filtered,
                                                  key="node_selector")
                    if selected_node:
                        spec = node_info[selected_node]
                        st.markdown(f"**{selected_node}**")
                        st.markdown(f"Category: `{spec.get('category', 'N/A')}`")
                        st.markdown(f"Description: {spec.get('description', 'N/A')}")
                        with st.expander("📥 Inputs", expanded=True):
                            for name, inp in spec.get("input", {}).get("required", {}).items():
                                st.code(f"{name}: {json.dumps(inp, indent=2)[:200]}",
                                        language="")
                        with st.expander("📤 Outputs"):
                            for i, out in enumerate(spec.get("output", [])):
                                st.code(f"[{i}] {out}", language="")
                except Exception as e:
                    st.error(f"Failed to fetch node info: {e}")
        else:
            st.warning("ComfyUI is offline. Start it to explore nodes.")

# ═══════════════════════════════════════════════════════════
# TAB 4: OUTPUTS
# ═══════════════════════════════════════════════════════════
with tab_outputs:
    st.subheader("📁 Generated Content")

    all_outputs = list(OUTPUT_DIR.rglob("*")) if OUTPUT_DIR.exists() else []
    all_outputs = [f for f in all_outputs if f.is_file() and
                   f.suffix in (".mp4", ".wav", ".png", ".jpg", ".srt")]

    if all_outputs:
        videos = [f for f in all_outputs if f.suffix == ".mp4"]
        images = [f for f in all_outputs if f.suffix in (".png", ".jpg")]
        audios = [f for f in all_outputs if f.suffix in (".wav", ".mp3")]
        subtitles = [f for f in all_outputs if f.suffix == ".srt"]

        if videos:
            st.markdown("### 🎬 Videos")
            cols = st.columns(2)
            for i, vf in enumerate(videos):
                with cols[i % 2]:
                    st.video(str(vf))
                    c1, c2 = st.columns(2)
                    c1.download_button("⬇️ Download",
                                       data=open(vf, "rb"),
                                       file_name=vf.name,
                                       use_container_width=True)
                    if c2.button("🗑️", key=f"del_{vf.name}",
                                 use_container_width=True):
                        vf.unlink()
                        st.rerun()

        if images:
            st.markdown("### 🖼️ Images")
            cols = st.columns(4)
            for i, imgf in enumerate(images):
                with cols[i % 4]:
                    st.image(str(imgf), use_container_width=True)
                    st.caption(imgf.name)

        if audios:
            st.markdown("### 🎵 Audio")
            for af in audios:
                st.audio(str(af))
                st.caption(af.name)

        if subtitles:
            st.markdown("### 📝 Subtitles")
            for sf in subtitles:
                with st.expander(sf.name):
                    st.text(sf.read_text(encoding="utf-8"))

        col_clear, _ = st.columns([1, 3])
        with col_clear:
            if st.button("🗑️ Clear All", type="primary",
                         use_container_width=True):
                for f in all_outputs:
                    f.unlink()
                st.rerun()
    else:
        st.info("No outputs yet. Generate something in News Studio or Chat!")
        st.markdown("""
        <div class="card" style="text-align:center;padding:2rem;">
            <span style="font-size:3rem;">🎬</span>
            <h3 style="color:#d4a017;">Ready to create?</h3>
            <p style="color:#7a8ba8;">
                Go to <strong>AI Chat & Help</strong> or <strong>News Studio</strong><br>
                to generate your first news reel!
            </p>
        </div>
        """, unsafe_allow_html=True)



