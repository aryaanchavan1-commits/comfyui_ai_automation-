import os
import json
import re
import time
from typing import Optional
from openai import OpenAI
from config import LLM_MODEL, OPENCODE_ZEN_API_KEY, OPENCODE_ZEN_BASE_URL

SYSTEM_PROMPT = """You are Sagarwave AI, a professional news production agent.
Your role is to create high-quality broadcast news content.

CAPABILITIES:
- Generate professional news scripts in English, Hindi, Marathi, Gujarati
- Auto-enhance user requests for maximum production quality  
- Plan ComfyUI workflows for news video production
- Optimize prompts for AI image/video generation

QUALITY STANDARDS:
- Scripts must be engaging, factual, and broadcast-ready
- Use professional news anchor language
- Include proper pacing for 150 words per minute
- Structure: powerful headline → engaging intro → detailed story → highlights → strong closing

When given a task, ALWAYS auto-enhance the user's request for professional quality.
Respond with valid JSON containing:
- enhanced_prompt: the upgraded version of what the user asked for
- task_analysis: what's needed
- workflow_plan: step-by-step ComfyUI pipeline
- script: full broadcast-ready news script
- parameters: optimal model/workflow settings (always use high quality)
- language: the language for TTS/script

Always use the highest quality parameters. Never compromise on quality."""

PROFESSIONAL_ENHANCEMENTS = {
    "visual_prompt_prefix": (
        "professional broadcast quality, cinematic lighting, 8K, "
        "news studio production, highly detailed, dramatic composition, "
        "sharp focus, vibrant colors"
    ),
    "negative_prompt": (
        "blurry, low quality, distorted, watermark, text, signature, "
        "amateur, noisy, dark, underexposed, cartoon, anime"
    ),
    "t2i_params": {"steps": 30, "cfg": 7.5, "sampler": "dpmpp_2m", "scheduler": "karras"},
    "video_params": {"fps": 30, "bitrate": "8M", "codec": "h264_nvenc"},
}

WORKFLOW_GEN_PROMPT = """You are Sagarwave AI, a ComfyUI workflow expert.
You generate VALID ComfyUI workflow JSON based on user requests.

NODE REFERENCE (input specs for available nodes):
{node_specs}

CONNECTION RULES:
- Each node has outputs you can reference: ["node_id", output_index]
- Always connect: CheckpointLoaderSimple → model to KSampler, clip to CLIPTextEncode, vae to VAEDecode
- Always end with SaveImage (for images) or SaveVideo (for video)
- Use unique numeric string IDs for each node ("1", "2", "3"...)

Respond with ONLY valid JSON containing:
- workflow: the workflow JSON object  
- model_needed: the checkpoint/model filename needed
- recommended_models: list of {"name": str, "folder": str} to download
- explanation: brief description of the workflow"""


class AgentBrain:
    def __init__(self):
        self.client = None
        self.conversation_history = []
        self.node_cache = {}
        self._init_llm()

    def _init_llm(self):
        if OPENCODE_ZEN_API_KEY:
            self.client = OpenAI(
                api_key=OPENCODE_ZEN_API_KEY,
                base_url=OPENCODE_ZEN_BASE_URL,
            )

    def available(self) -> bool:
        return self.client is not None

    def cache_nodes(self, node_info: dict):
        self.node_cache = node_info

    def _condense_node_specs(self, node_info: dict) -> str:
        lines = []
        for name, spec in list(node_info.items())[:60]:
            inputs = spec.get("input", {}).get("required", {})
            in_str = ", ".join(list(inputs.keys())[:8])
            outputs = spec.get("output", [])
            out_str = ", ".join(str(o) for o in outputs[:4])
            cat = spec.get("category", "")
            lines.append(f"- {name} (cat:{cat}) inputs:[{in_str}] outputs:[{out_str}]")
        return "\n".join(lines)

    # ─── Full Autonomous Execution ──────────────────────

    def execute_autonomous(self, user_request: str,
                           comfy=None, model_mgr=None) -> dict:
        steps = []
        errors = []

        steps.append({"step": "discover_nodes", "status": "running"})
        try:
            node_info = comfy.get_object_info() if comfy else {}
            self.cache_nodes(node_info)
            available = sorted(node_info.keys())
            steps[-1] = {"step": "discover_nodes", "status": "done",
                         "count": len(available)}
        except Exception as e:
            errors.append(f"Node discovery: {e}")
            available = []

        steps.append({"step": "generate_workflow", "status": "running"})
        try:
            wf_result = self.generate_workflow(user_request, available,
                                                node_info)
            workflow = wf_result.get("workflow", {})
            model_needed = wf_result.get("model_needed", "")
            rec_models = wf_result.get("recommended_models", [])
            steps[-1] = {"step": "generate_workflow", "status": "done",
                         "model_needed": model_needed}
        except Exception as e:
            errors.append(f"Workflow generation: {e}")
            workflow = self._fallback_workflow(user_request)
            model_needed = ""
            rec_models = []

        steps.append({"step": "ensure_models", "status": "running"})
        try:
            model_suggestions = self.suggest_models(user_request)
            for suggestion in model_suggestions:
                if model_mgr:
                    model_mgr.download_if_missing(
                        suggestion["name"], suggestion["folder"]
                    )
            for rec in rec_models:
                if model_mgr and isinstance(rec, dict):
                    model_mgr.download_if_missing(
                        rec.get("name", rec.get("model", "")),
                        rec.get("folder", "checkpoints")
                    )
            steps[-1] = {"step": "ensure_models", "status": "done"}
        except Exception as e:
            errors.append(f"Model management: {e}")

        steps.append({"step": "validate_workflow", "status": "running"})
        try:
            validation = self.validate_workflow(workflow, node_info)
            if validation["valid"]:
                steps[-1] = {"step": "validate_workflow", "status": "done"}
            else:
                steps[-1] = {"step": "validate_workflow", "status": "warning",
                             "issues": validation["issues"]}
        except Exception as e:
            errors.append(f"Validation: {e}")

        return {
            "workflow": workflow,
            "model_needed": model_needed,
            "recommended_models": rec_models,
            "steps": steps,
            "errors": errors,
        }

    def validate_workflow(self, workflow: dict, node_info: dict) -> dict:
        issues = []
        if not workflow:
            return {"valid": False, "issues": ["Empty workflow"]}
        for node_id, node in workflow.items():
            ct = node.get("class_type", "")
            if ct not in node_info:
                issues.append(f"Node {node_id}: unknown class_type '{ct}'")
            else:
                spec = node_info[ct]
                required = spec.get("input", {}).get("required", {})
                for inp_name in required:
                    if inp_name not in node.get("inputs", {}):
                        issues.append(f"Node {node_id} ({ct}): missing input '{inp_name}'")
        has_save = any(
            n.get("class_type", "").startswith("Save")
            for n in workflow.values()
        )
        if not has_save:
            issues.append("No SaveImage/SaveVideo node found")
        return {"valid": len(issues) == 0, "issues": issues}

    # ─── Public API ──────────────────────────────────────

    def plan_from_request(self, user_input: str,
                          uploaded_files: Optional[list[str]] = None) -> dict:
        enhanced = self.auto_enhance_prompt(user_input)
        if self.available():
            return self._query_llm(enhanced, uploaded_files)
        return self._fallback_plan(enhanced, uploaded_files)

    def generate_news_script(self, topic: str, language: str = "English",
                             duration: int = 60) -> dict:
        enhanced = self.auto_enhance_prompt(
            f"Generate a {language} news script about '{topic}' "
            f"for {duration} seconds"
        )
        if self.available():
            return self._query_llm(
                f"{enhanced}\n\nInclude headline, introduction, main story, "
                f"highlights, and conclusion."
            )
        plan = self._fallback_plan(enhanced)
        return plan.get("script", plan)

    def auto_enhance_prompt(self, raw_input: str) -> str:
        enhancements = [
            "Create a professional, broadcast-quality news production",
            "Use cinematic visuals and professional anchor presentation",
            "Ensure clear, engaging delivery with proper pacing",
            "Optimize for social media reels with high production value",
            "Include professional news graphics and transitions",
        ]
        if len(raw_input) < 50:
            raw_input = raw_input + " " + enhancements[
                hash(raw_input) % len(enhancements)
            ]
        return raw_input

    def enhance_visual_prompt(self, base_prompt: str) -> str:
        prefix = PROFESSIONAL_ENHANCEMENTS["visual_prompt_prefix"]
        return f"{prefix}, {base_prompt}"

    def get_negative_prompt(self) -> str:
        return PROFESSIONAL_ENHANCEMENTS["negative_prompt"]

    def get_quality_params(self, duration: int = 60) -> dict:
        params = dict(PROFESSIONAL_ENHANCEMENTS["t2i_params"])
        if duration > 120:
            params["steps"] = 30
        elif duration > 60:
            params["steps"] = 25
        params["cfg"] = 7.5
        return params

    # ─── LLM Query ───────────────────────────────────────

    def _query_llm(self, user_input: str,
                   uploaded_files: Optional[list[str]] = None) -> dict:
        file_context = ""
        if uploaded_files:
            file_context = f"\nUser has uploaded files: {', '.join(uploaded_files)}"

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *self.conversation_history[-10:],
            {
                "role": "user",
                "content": f"{user_input}{file_context}\n\n"
                           f"Respond with a JSON plan."
            }
        ]

        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                temperature=0.3,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            result = json.loads(content)
            self.conversation_history.append(
                {"role": "user", "content": user_input}
            )
            self.conversation_history.append(
                {"role": "assistant", "content": json.dumps(result)}
            )
            return result
        except Exception as e:
            return {
                "error": str(e),
                "task_analysis": f"LLM failed, using fallback: {e}",
                "workflow_plan": self._fallback_plan(user_input, uploaded_files),
            }

    # ─── Fallback  ───────────────────────────────────────

    def _fallback_plan(self, user_input: str,
                       uploaded_files: Optional[list[str]] = None) -> dict:
        input_lower = user_input.lower()

        languages = []
        for lang, code in [("marathi", "Marathi"), ("hindi", "Hindi"),
                           ("english", "English"), ("gujarati", "Gujarati")]:
            if lang in input_lower:
                languages.append(code)
        if not languages:
            languages.append("English")

        duration = 60
        m = re.search(r"(\d+)\s*(min|sec|s|m)", input_lower)
        if m:
            n, u = int(m.group(1)), m.group(2)
            duration = n * 60 if u in ("min", "m") else n

        topic = re.sub(r"(create|make|generate|about|for|news|video|in)\s+",
                       "", input_lower, flags=re.I).strip()[:100]
        topic = topic or "breaking news"

        words_needed = int(duration * 2.3)
        return {
            "task_analysis": {
                "topic": topic, "languages": languages,
                "target_duration": duration,
                "quality": "professional broadcast",
                "has_images": any(f and f.endswith((".png", ".jpg", ".jpeg"))
                                  for f in (uploaded_files or [])),
                "has_audio": any(f and f.endswith((".wav", ".mp3", ".m4a"))
                                 for f in (uploaded_files or [])),
            },
            "workflow_plan": {
                "steps": [
                    {"step": 1, "action": "generate_news_script",
                     "params": {"topic": topic, "languages": languages,
                                "duration": duration}},
                    {"step": 2, "action": "create_tts_audio",
                     "params": {"language": languages[0], "duration": duration}},
                    {"step": 3, "action": "generate_professional_visuals",
                     "params": {"topic": topic, "count": 5}},
                    {"step": 4, "action": "create_talking_head",
                     "params": {"use_uploaded_image": True}},
                    {"step": 5, "action": "compose_professional_video",
                     "params": {"resolution": (1080, 1920),
                                "add_subtitles": True}},
                ]
            },
            "script": self._generate_pro_script(topic, languages[0], words_needed),
            "parameters": {
                "model": "flux1-dev.safetensors",
                "steps": 30, "cfg": 7.5,
                "sampler": "dpmpp_2m", "scheduler": "karras",
                "resolution": (1080, 1920), "fps": 30,
                "bitrate": "8M",
            }
        }

    def _generate_pro_script(self, topic: str, language: str,
                              words: int) -> dict:
        body_words = max(50, words - 60)
        return {
            "headline": f"BREAKING NEWS: {topic.upper()} — "
                        f"Latest Developments That Matter",
            "introduction": (
                f"Good evening, and welcome to Sagarwave News Studio. "
                f"I'm your anchor, and this is your comprehensive coverage of "
                f"{topic}. In today's broadcast, we bring you in-depth analysis, "
                f"expert perspectives, and the latest updates you need to know."
            ),
            "main_story": (
                f"In a significant development regarding {topic}, sources "
                f"confirm that this story is rapidly evolving. Our reporters "
                f"on the ground have been tracking every angle to bring you "
                f"the most accurate and timely information. "
                + " ".join([
                    f"This situation continues to develop, and our team is "
                    f"committed to bringing you the latest updates as they "
                    f"happen. We're analyzing the impact on local communities "
                    f"and the broader implications for our viewers."
                ] * max(1, body_words // 30))
            ),
            "highlights": [
                f"Breaking: Major developments in {topic}",
                f"Expert analysis and data-driven insights",
                f"Impact on local and national communities",
                f"Official statements and reactions",
                f"What to expect in the coming days",
            ],
            "conclusion": (
                f"That brings us to the end of this special coverage on "
                f"{topic}. We'll continue to monitor this story and bring you "
                f"updates as they develop. This has been Sagarwave News Studio — "
                f"your trusted source for news that matters. Stay informed, "
                f"stay connected, and we'll see you in our next broadcast."
            ),
            "language": language, "duration_seconds": words // 3,
        }

    # ─── Smart Workflow Generation ──────────────────────

    def generate_workflow(self, user_request: str,
                          available_nodes: list[str],
                          node_info: Optional[dict] = None) -> dict:
        if self.available() and node_info:
            return self._query_llm_workflow(user_request, node_info)
        return self._fallback_workflow(user_request)

    def _query_llm_workflow(self, user_request: str,
                             node_info: dict) -> dict:
        condensed = self._condense_node_specs(node_info)
        prompt = WORKFLOW_GEN_PROMPT.replace("{node_specs}", condensed)
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user",
             "content": f"Generate a ComfyUI workflow for: {user_request}"}
        ]
        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                temperature=0.1,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {
                "workflow": self._fallback_workflow(user_request),
                "model_needed": "sd_xl_base_1.0.safetensors",
                "recommended_models": [],
                "explanation": f"Fallback used (LLM error: {e})",
            }

    def _fallback_workflow(self, user_request: str) -> dict:
        req = user_request.lower()
        if "talking" in req or "avatar" in req or "head" in req or "portrait" in req:
            return {
                "1": {"class_type": "LoadImage",
                      "inputs": {"image": "anchor.png"}},
                "2": {"class_type": "LoadAudio",
                      "inputs": {"audio": "voice.wav"}},
                "3": {"class_type": "LivePortrait",
                      "inputs": {"image": ["1", 0], "audio": ["2", 0],
                                 "face_scale": 1.0,
                                 "face_offset_x": 0, "face_offset_y": 0}},
                "4": {"class_type": "VHS_VideoCombine",
                      "inputs": {"images": ["3", 0], "frame_rate": 30,
                                 "loop_count": 1,
                                 "filename_prefix": "sagarwave_output"}},
                "5": {"class_type": "SaveVideo",
                      "inputs": {"video": ["4", 0],
                                 "filename_prefix": "sagarwave_final"}},
            }
        if "upscale" in req or "enhance" in req:
            return {
                "1": {"class_type": "LoadImage",
                      "inputs": {"image": "input.png"}},
                "2": {"class_type": "ImageUpscaleWithModel",
                      "inputs": {"upscale_model": ["3", 0],
                                 "image": ["1", 0]}},
                "3": {"class_type": "UpscaleModelLoader",
                      "inputs": {"model_name": "4x_NMKD-Superscale-SP_178000_G.pth"}},
                "4": {"class_type": "SaveImage",
                      "inputs": {"filename_prefix": "upscaled",
                                 "images": ["2", 0]}},
            }
        if "video" in req or "animate" in req:
            return {
                "1": {"class_type": "CheckpointLoaderSimple",
                      "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}},
                "2": {"class_type": "CLIPTextEncode",
                      "inputs": {"text": user_request, "clip": ["1", 1]}},
                "3": {"class_type": "CLIPTextEncode",
                      "inputs": {"text": "blurry, low quality",
                                 "clip": ["1", 1]}},
                "4": {"class_type": "EmptyLatentImage",
                      "inputs": {"width": 512, "height": 512, "batch_size": 16}},
                "5": {"class_type": "KSampler",
                      "inputs": {"seed": 42, "steps": 20, "cfg": 7.0,
                                 "sampler_name": "euler",
                                 "scheduler": "normal", "denoise": 1.0,
                                 "model": ["1", 0],
                                 "positive": ["2", 0],
                                 "negative": ["3", 0],
                                 "latent_image": ["4", 0]}},
                "6": {"class_type": "VAEDecode",
                      "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
                "7": {"class_type": "VHS_VideoCombine",
                      "inputs": {"images": ["6", 0], "frame_rate": 8,
                                 "loop_count": 1,
                                 "filename_prefix": "animation"}},
            }
        if "control" in req or "canny" in req or "depth" in req or "pose" in req:
            return {
                "1": {"class_type": "CheckpointLoaderSimple",
                      "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}},
                "2": {"class_type": "CLIPTextEncode",
                      "inputs": {"text": user_request, "clip": ["1", 1]}},
                "3": {"class_type": "CLIPTextEncode",
                      "inputs": {"text": "low quality", "clip": ["1", 1]}},
                "4": {"class_type": "LoadImage",
                      "inputs": {"image": "input.png"}},
                "5": {"class_type": "CannyEdgePreprocessor",
                      "inputs": {"image": ["4", 0], "low_threshold": 100,
                                 "high_threshold": 200}},
                "6": {"class_type": "ControlNetLoader",
                      "inputs": {"control_net_name": "control_v11p_sd15_canny.pth"}},
                "7": {"class_type": "ControlNetApply",
                      "inputs": {"conditioning": ["2", 0],
                                 "control_net": ["6", 0],
                                 "image": ["5", 0], "strength": 0.8}},
                "8": {"class_type": "EmptyLatentImage",
                      "inputs": {"width": 512, "height": 512, "batch_size": 1}},
                "9": {"class_type": "KSampler",
                      "inputs": {"seed": 42, "steps": 25, "cfg": 7.0,
                                 "sampler_name": "dpmpp_2m",
                                 "scheduler": "karras", "denoise": 1.0,
                                 "model": ["1", 0],
                                 "positive": ["7", 0],
                                 "negative": ["3", 0],
                                 "latent_image": ["8", 0]}},
                "10": {"class_type": "VAEDecode",
                       "inputs": {"samples": ["9", 0], "vae": ["1", 2]}},
                "11": {"class_type": "SaveImage",
                       "inputs": {"filename_prefix": "controlnet_output",
                                  "images": ["10", 0]}},
            }
        return {
            "1": {"class_type": "CheckpointLoaderSimple",
                  "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}},
            "2": {"class_type": "CLIPTextEncode",
                  "inputs": {"text": user_request, "clip": ["1", 1]}},
            "3": {"class_type": "CLIPTextEncode",
                  "inputs": {"text": "text, watermark, low quality, blurry",
                             "clip": ["1", 1]}},
            "4": {"class_type": "EmptyLatentImage",
                  "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
            "5": {"class_type": "KSampler",
                  "inputs": {"seed": int(time.time()), "steps": 25,
                             "cfg": 7.0, "sampler_name": "dpmpp_2m",
                             "scheduler": "karras", "denoise": 1.0,
                             "model": ["1", 0], "positive": ["2", 0],
                             "negative": ["3", 0],
                             "latent_image": ["4", 0]}},
            "6": {"class_type": "VAEDecode",
                  "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
            "7": {"class_type": "SaveImage",
                  "inputs": {"filename_prefix": "sagarwave_output",
                             "images": ["6", 0]}},
        }

    def suggest_models(self, user_request: str) -> list[dict]:
        req = user_request.lower()
        suggestions = []
        model_map = {
            "flux": ("Flux.1 Dev", "checkpoints"),
            "sdxl": ("SDXL base 1.0", "checkpoints"),
            "realistic": ("Realistic Vision V6", "checkpoints"),
            "dreamshaper": ("DreamShaper XL", "checkpoints"),
            "lora": ("Detail Enhancer LoRA", "loras"),
            "vae": ("SDXL VAE", "vae"),
            "controlnet": ("Canny ControlNet", "controlnet"),
            "liveportrait": ("LivePortrait", "liveportrait"),
            "insightface": ("InsightFace", "insightface"),
            "ip": ("IPAdapter", "ipadapter"),
            "upscale": ("4x_NMKD Upscaler", "upscale_models"),
        }
        for keyword, (name, folder) in model_map.items():
            if keyword in req:
                suggestions.append({"name": name, "folder": folder})
        if not suggestions:
            suggestions.append({"name": "SDXL base 1.0", "folder": "checkpoints"})
        return suggestions

    # ─── Helpers ─────────────────────────────────────────

    def suggest_workflow_params(self, task: str) -> dict:
        params = dict(PROFESSIONAL_ENHANCEMENTS["t2i_params"])
        if "portrait" in task.lower() or "live" in task.lower():
            params.update({"class_type": "LivePortrait",
                           "face_scale": 1.0, "face_offset": (0, 0)})
        return params

    def clear_history(self):
        self.conversation_history = []
