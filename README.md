# Sagarwave AI Agent

> An AI-powered professional news video production system — script writing, mood detection, text-to-image, talking head animation, and video composition, all driven by DeepSeek V4 Flash (via OpenCode Zen) and ComfyUI.

**Created by Aryan Chavan**

---

## Features

- **🎙️ Audio → News Pipeline** — Upload audio, auto-transcribe via Whisper, detect mood, generate a broadcast-ready news script, and produce a complete video
- **📝 AI Script Generation** — DeepSeek V4 Flash (free via OpenCode Zen) writes professional news scripts in English, Hindi, Marathi, Gujarati
- **🎭 Mood Detection** — Classifies news tone (breaking, serious, sad, inspirational, informational) and adjusts visuals, colors, pacing accordingly
- **🖼️ Text-to-Image + Talking Head** — Generates news anchor visuals with SDXL/Flux, then animates them with LivePortrait
- **🎞️ AnimateDiff Integration** — Optional motion video segments for dynamic news b-roll
- **🎨 Royal Dark UI** — Professional Streamlit interface with tabs for audio processing, script editing, pipeline control, and model management
- **📦 Model Manager** — Built-in model download, discovery, and recommendation engine

---

## Prerequisites

| Requirement | Version / Notes |
|---|---|
| **Python** | 3.10+ (3.11 recommended) |
| **ComfyUI** | Standalone install with custom nodes (see below) |
| **FFmpeg** | Required for video/audio processing |
| **CUDA GPU** | 8 GB+ VRAM for SDXL; 24 GB+ for Flux.1 Dev |

### Required ComfyUI Custom Nodes

Install in your `ComfyUI/custom_nodes/` directory:

- [ComfyUI-Manager](https://github.com/ltdrdata/ComfyUI-Manager)
- [ComfyUI-AnimateDiff-Evolved](https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved)
- [ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite)
- [ComfyUI-LivePortraitKJ](https://github.com/kijai/ComfyUI-LivePortraitKJ)

---

## Installation

### 1. Clone & set up environment

```bash
git clone https://github.com/aryaanchavan1-commits/comfyui_ai_automation-.git
cd comfyui_ai_automation-
python -m venv venv
venv\Scripts\activate   # Windows
# or: source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy `.env.example` to `.env` and fill in your values:

```bash
copy .env.example .env   # Windows
# or: cp .env.example .env  # Linux/Mac
```

Edit `.env`:

```env
# ─── Sagarwave AI Agent ─────────────────────
# OpenCode Zen API - Free DeepSeek V4 Flash
LLM_PROVIDER=opencode_zen
LLM_MODEL=deepseek-v4-flash-free
OPENCODE_ZEN_API_KEY=your_api_key_here
OPENCODE_ZEN_BASE_URL=https://opencode.ai/zen/v1

# ComfyUI Connection
COMFYUI_URL=http://127.0.0.1:8188

# Hugging Face Token (for gated model downloads like Flux.1 Dev)
HF_TOKEN=hf_your_token_here
```

> **Get an API key:** Sign up at [opencode.ai](https://opencode.ai) for a free DeepSeek V4 Flash key.

### 3. Configure ComfyUI path

The system expects ComfyUI at `C:\Users\sagarwave\ComfyUI-Installs\ComfyUI (1)\ComfyUI` by default.  
Edit `config.py` to change `BASE_DIR` or `COMFYUI_BASE` to match your installation.

### 4. Download models

Run the automated model installer:

```bash
python install_models.py
```

This will download:

| Model | Size | Folder |
|---|---|---|
| SDXL base 1.0 | 6.9 GB | `checkpoints/` |
| SDXL VAE | 335 MB | `vae/` |
| Flux.1 Dev | 23.8 GB | `diffusion_models/` |
| Realistic Vision V6 | 6.0 GB | `checkpoints/` |
| 4x-UltraSharp upscaler | 67 MB | `upscale_models/` |
| SDXL Detail Enhancer LoRA | 228 MB | `loras/` |
| InsightFace buffalo_l | ~290 MB | `insightface/buffalo_l/` |
| LivePortrait models | ~630 MB | `liveportrait/` |

> **Note:** Flux.1 Dev is a gated model — you must accept its license on [HuggingFace](https://huggingface.co/black-forest-labs/FLUX.1-dev) and set `HF_TOKEN` in `.env`.

### 5. Launch

```bash
python app.py
# or double-click launch.bat
```

This starts the Streamlit app at `http://localhost:8501`.

---

## Usage

### Tab 1: Audio Upload & Analysis

1. Upload an audio file (MP3, WAV, M4A — up to 200 MB)
2. The system transcribes it with Whisper, detects mood, and extracts the news topic
3. Review the transcript and detected mood

### Tab 2: Script Generation

1. Review / edit the auto-detected news topic
2. Select language (English, Hindi, Marathi, Gujarati)
3. Set video duration (15–300 seconds)
4. Click **Generate News Script** — uses DeepSeek V4 Flash via OpenCode Zen
5. Edit the generated script inline if needed

### Tab 3: Visual Preview

- View mood-adapted color themes
- Preview generated anchor images and scenes
- Configure image grid and aspect ratio

### Tab 4: Pipeline Execution

| Step | Description |
|---|---|
| 1. Script Generation | Generates broadcast-ready news script via LLM |
| 2. Voice Over | Creates/loads audio track |
| 3. Visual Generation | SDXL/Flux T2I → anchor image + scene visuals |
| 4. Talking Head | LivePortrait animation of anchor image |
| 5. Video Composition | MoviePy assembly with transitions, overlays, captions |
| 6. Export | Final MP4 with configurable resolution and bitrate |

Click **Run Full Pipeline** or execute individual steps.

### Tab 5: Model Management

- List installed models across all categories
- Discover and download recommended models
- Search HuggingFace for specific models

---

## Project Structure

```
comfyui_agent/
├── app.py                 # Streamlit UI — tabs, styling, user interaction
├── config.py              # Environment variables, paths, mood themes, quality presets
├── agent_core.py          # LLM integration (AgentBrain class, script generation, prompt enhancement)
├── pipeline_manager.py    # Pipeline orchestration (news video production workflow)
├── comfyui_automator.py   # ComfyUI API client (workflow execution, model listing)
├── emotion_analyzer.py    # Whisper transcription + LLM-based mood detection
├── model_manager.py       # Model discovery, download, folder mapping
├── install_models.py      # Automated model download script with progress bars
├── launch.bat             # One-click install + launch
├── requirements.txt       # Python dependencies
├── .env                   # Local configuration (DO NOT COMMIT)
├── .env.example           # Environment variable template
├── outputs/               # Generated videos and images
└── workflow_templates/    # ComfyUI workflow JSON templates
```

---

## API Reference

### `AgentBrain` (agent_core.py)

The brain of the system — interfaces with DeepSeek V4 Flash via OpenCode Zen API.

```python
brain = AgentBrain()

# Generate a complete broadcast news script
script = brain.generate_news_script(
    topic="Stock market reaches all-time high",
    language="English",
    duration=60  # seconds
)
# Returns: { "full_text": "...", "headline": "...", "segments": [...], ... }

# Enhance any prompt for professional quality
enhanced = brain.enhance_prompt("a news anchor in a studio")
# Returns: "professional broadcast quality, cinematic lighting, ..."

# Get ComfyUI workflow suggestions
workflow = brain.generate_workflow(
    task_description="Create a talking head animation",
    available_nodes=[...]
)

# Chat with the agent
response = brain.chat("Generate a script about climate change")
```

### `PipelineManager` (pipeline_manager.py)

Orchestrates the full news video production pipeline.

```python
manager = PipelineManager(comfy_automator, agent_brain, mood="informational")

# Execute the full pipeline
result = manager.execute_news_pipeline(
    topic="Election results announced",
    language="English",
    duration=60,
    anchor_image="path/to/anchor.png",   # optional
    voice_audio="path/to/audio.mp3",     # optional, uses TTS if omitted
    news_images=["img1.png", "img2.png"], # optional scene images
    mood="breaking",                      # auto-detected if omitted
    progress_callback=my_progress_fn      # optional callback
)
# Returns pipeline state dict with status, outputs, each step's result

# Get current pipeline state
state = manager.get_state()

# Access mood theme config
theme = manager._get_theme()  # { "mood": "...", "colors": {...}, "prefix": "...", ... }
```

Available moods: `"breaking"`, `"serious"`, `"sad"`, `"inspirational"`, `"informational"`

### `emotion_analyzer` (emotion_analyzer.py)

Transcribes audio and detects emotional tone.

```python
from emotion_analyzer import transcribe_audio, detect_mood, extract_topic_from_audio

# Transcribe audio file
text = transcribe_audio("path/to/audio.mp3")
# Returns: "transcribed text as a single string"

# Detect mood from audio file
mood_result = detect_mood("path/to/audio.mp3")
# Returns: { "mood": "informational", "confidence": 0.85, "reason": "..." }

# Extract topic from audio
topic = extract_topic_from_audio("path/to/audio.mp3")
# Returns: "Extracted news topic string"
```

### `ModelManager` (model_manager.py)

Discover, download, and manage AI models.

```python
manager = ModelManager(comfy_automator)

# Map model type to ComfyUI folder
folder = manager.discover_folder("sdxl checkpoint")
# Returns: "checkpoints"

# Suggest folder based on model name keywords
folder = manager.suggest_folder("my_lora_style.safetensors")
# Returns: "loras"

# Get recommended models
from model_manager import RECOMMENDED_MODELS
# Dict of { folder_name: { display_name: download_url } }

# Install a remote model
result = manager.install_model(
    model_url="https://huggingface.co/.../model.safetensors",
    folder_name="checkpoints",
    filename="my_model.safetensors"
)
```

### `ComfyUIAutomator` (comfyui_automator.py)

Low-level ComfyUI HTTP API client.

```python
automator = ComfyUIAutomator(base_url="http://127.0.0.1:8188")

# List installed models
models = automator.list_models(folder="checkpoints")

# Execute a workflow
result = automator.execute_workflow(workflow_json, timeout=300)

# Get queue status
status = automator.get_queue_status()

# Interrupt generation
automator.interrupt()
```

### `config` (config.py)

Central configuration module. Key exports:

| Variable | Type | Default | Description |
|---|---|---|---|
| `LLM_PROVIDER` | str | `"opencode_zen"` | LLM backend |
| `LLM_MODEL` | str | `"deepseek-v4-flash-free"` | Model name |
| `OPENCODE_ZEN_API_KEY` | str | env var | API key |
| `OPENCODE_ZEN_BASE_URL` | str | `"https://opencode.ai/zen/v1"` | API endpoint |
| `COMFYUI_URL` | str | `"http://127.0.0.1:8188"` | ComfyUI server |
| `HF_TOKEN` | str | env var | HuggingFace token |
| `OUTPUT_DIR` | Path | `outputs/` | Generated media |
| `WORKFLOW_DIR` | Path | `workflow_templates/` | Workflow JSONs |
| `MOOD_THEMES` | dict | — | Colors, visual prefixes per mood |
| `SUPPORTED_LANGUAGES` | list | `["English", "Hindi", ...]` | Available languages |
| `RESOLUTIONS` | dict | — | Output resolutions |

---

## Model Requirements

### Minimum Recommended Models

| Model | Purpose | Source |
|---|---|---|
| SDXL base 1.0 | Primary text-to-image | stabilityai on HF |
| SDXL VAE | Image quality | stabilityai on HF |
| Realistic Vision V6 | Photorealistic anchor images | SG161222 on HF |
| 4x-UltraSharp | Upscaling | FrozenLake on HF |
| LivePortrait models | Talking head animation | Kijai on HF |
| InsightFace buffalo_l | Face detection (fallback) | deepinsight on GitHub |

### Optional Models

| Model | Purpose |
|---|---|
| Flux.1 Dev | Highest quality T2I (24 GB VRAM recommended) |
| DreamShaper XL | Artistic/creative styles |
| AnimateDiff models | Motion video (b-roll segments) |
| SDXL Detail Enhancer LoRA | Fine detail enhancement |

---

## Troubleshooting

| Problem | Solution |
|---|---|
| **"401 Unauthorized"** on model download | Set `HF_TOKEN` in `.env` and accept the model license on HuggingFace |
| **ComfyUI connection refused** | Ensure ComfyUI is running (`python main.py` in ComfyUI folder) |
| **CUDA out of memory** | Reduce resolution in config, use SDXL instead of Flux, enable `--lowvram` in ComfyUI |
| **LivePortrait fails** | Install MediaPipe: `pip install mediapipe` and ensure InsightFace models are in `models/insightface/` |
| **No audio in output video** | Verify FFmpeg is installed and in PATH |
| **Whisper is slow** | Install `faster-whisper` with CUDA support, or switch to `tiny` model |
| **LLM returns gibberish** | Check `OPENCODE_ZEN_API_KEY` is valid; try a different `LLM_MODEL` |

---

## License

This project is for educational and personal use. Models have their own licenses — refer to each model's HuggingFace page for terms.

---

*Created by [Aryan Chavan](https://github.com/aryaanchavan1-commits)*
