import os
import json
import time
import math
import logging
from pathlib import Path
from typing import Optional, Callable
from config import OUTPUT_DIR, WORKFLOW_DIR, MOOD_THEMES, DEFAULT_MOOD
from comfyui_automator import ComfyUIAutomator
from agent_core import AgentBrain
from emotion_analyzer import extract_topic_from_audio, detect_mood

logger = logging.getLogger("sagarwave.pipeline")


class PipelineManager:
    def __init__(self, comfy: ComfyUIAutomator, brain: AgentBrain, mood: str = None):
        self.comfy = comfy
        self.brain = brain
        self.mood = mood or DEFAULT_MOOD
        self.pipeline_state = {
            "id": "",
            "status": "idle",
            "steps": [],
            "current_step": 0,
            "outputs": [],
            "error": None,
        }

    def set_mood(self, mood: str):
        self.mood = mood if mood in MOOD_THEMES else DEFAULT_MOOD

    def _get_theme(self) -> dict:
        return MOOD_THEMES.get(self.mood, MOOD_THEMES[DEFAULT_MOOD])

    def get_state(self) -> dict:
        return self.pipeline_state

    def execute_news_pipeline(
        self,
        topic: str,
        language: str = "English",
        duration: int = 60,
        anchor_image: Optional[str] = None,
        voice_audio: Optional[str] = None,
        news_images: Optional[list[str]] = None,
        mood: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
    ) -> dict:
        self.mood = mood if mood and mood in MOOD_THEMES else self.mood
        self.pipeline_state = {
            "id": str(int(time.time())),
            "status": "running",
            "mood": self.mood,
            "steps": [],
            "current_step": 0,
            "outputs": [],
            "error": None,
        }

        try:
            self._report(progress_callback, 1, 5, "Generating news script...")
            script = self.brain.generate_news_script(topic, language, duration)
            full_text = script.get("full_text") or self._assemble_script(script)
            self.pipeline_state["steps"].append({
                "step": 1, "name": "Script", "status": "done",
                "script": script
            })

            self._report(progress_callback, 2, 5, "Creating voice over...")
            audio_result = self._create_audio(
                full_text, language, voice_audio
            )
            self.pipeline_state["steps"].append({
                "step": 2, "name": "Audio", "status": "done",
                "audio": audio_result
            })

            self._report(progress_callback, 3, 5,
                         f"Generating news visuals ({self.mood} mood)...")
            visuals = self._generate_visuals(
                topic, duration, news_images, self.mood, progress_callback
            )
            self.pipeline_state["steps"].append({
                "step": 3, "name": "Visuals", "status": "done",
                "visuals": visuals
            })

            self._report(progress_callback, 4, 5,
                         "Creating avatar with lip sync...")
            avatar = self._create_avatar(
                anchor_image, audio_result, progress_callback
            )
            self.pipeline_state["steps"].append({
                "step": 4, "name": "Avatar", "status": "done",
                "avatar": avatar
            })

            self._report(progress_callback, 5, 5,
                         f"Composing final news reel ({self.mood} mood)...")
            final = self._compose_video(
                avatar, visuals, audio_result,
                script, full_text, language, self.mood, progress_callback
            )
            self.pipeline_state["steps"].append({
                "step": 5, "name": "Compose", "status": "done",
                "final": final
            })
            self.pipeline_state["outputs"].append(final)
            self.pipeline_state["status"] = "completed"
            self._report(progress_callback, 5, 5,
                         f"Done! Output: {final}")

        except Exception as e:
            logger.error("Pipeline failed: %s", e)
            self.pipeline_state["status"] = "failed"
            self.pipeline_state["error"] = str(e)
            self._report(progress_callback, 0, 0, f"Error: {e}")

        return self.pipeline_state

    def _create_audio(self, text: str, language: str,
                      existing_audio: Optional[str] = None) -> str:
        if existing_audio and os.path.exists(existing_audio):
            return existing_audio

        try:
            import edge_tts
            import asyncio

            lang_voices = {
                "English": "en-IN-NeerjaNeural",
                "Hindi": "hi-IN-SwaraNeural",
                "Marathi": "mr-IN-AarohiNeural",
                "Gujarati": "gu-IN-DhwaniNeural",
            }
            voice = lang_voices.get(language, "en-IN-NeerjaNeural")
            out = str(OUTPUT_DIR / f"tts_{language}_{int(time.time())}.wav")

            CHUNK_LIMIT = 3000
            if len(text) <= CHUNK_LIMIT:
                async def _single():
                    c = edge_tts.Communicate(text, voice)
                    await c.save(out)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(_single())
                loop.close()
                return out

            chunks = [text[i:i+CHUNK_LIMIT]
                      for i in range(0, len(text), CHUNK_LIMIT)]
            chunk_files = []
            for idx, chunk in enumerate(chunks):
                chunk_path = str(OUTPUT_DIR / f"tts_{language}_chunk{idx}_{int(time.time())}.wav")
                async def _chunk(c=chunk, p=chunk_path, v=voice):
                    ct = edge_tts.Communicate(c, v)
                    await ct.save(p)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(_chunk())
                loop.close()
                chunk_files.append(chunk_path)

            if len(chunk_files) == 1:
                os.rename(chunk_files[0], out)
                return out

            from moviepy import AudioFileClip, concatenate_audioclips
            clips = [AudioFileClip(f) for f in chunk_files]
            combined = concatenate_audioclips(clips)
            combined.write_audiofile(out, fps=44100, logger=None)
            for c in clips:
                c.close()
            for f in chunk_files:
                try:
                    os.remove(f)
                except Exception as e:
                    logger.debug("Could not remove temp chunk %s: %s", f, e)
            return out

        except Exception as e:
            raise RuntimeError(f"TTS failed: {e}")

    def _generate_visuals(self, topic: str, duration: int = 60,
                          uploaded_images: Optional[list[str]] = None,
                          mood: str = None, progress_cb=None) -> list[str]:
        if uploaded_images and len(uploaded_images) > 0:
            visuals = []
            for i, img_path in enumerate(uploaded_images):
                if os.path.exists(img_path):
                    visuals.append(img_path)
            if visuals:
                return self._cycle_visuals(visuals, duration)

        theme = MOOD_THEMES.get(mood or DEFAULT_MOOD, MOOD_THEMES[DEFAULT_MOOD])
        mood_prefix = theme["visual_prefix"]

        visual_count = max(3, min(8, math.ceil(duration / 20)))
        prompts = [
            self.brain.enhance_visual_prompt(
                f"{mood_prefix}, professional news studio anchor desk, {topic}, "
                f"modern broadcast set, warm studio lighting"
            ),
            self.brain.enhance_visual_prompt(
                f"{mood_prefix}, journalists reporting on {topic}, newsroom with "
                f"multiple screens showing data, evening broadcast"
            ),
            self.brain.enhance_visual_prompt(
                f"{mood_prefix}, breaking news coverage of {topic}, large video wall "
                f"displaying latest updates, news studio wide shot"
            ),
            self.brain.enhance_visual_prompt(
                f"{mood_prefix}, newspaper headline about {topic} on desk, glasses, "
                f"morning news setup, warm and professional"
            ),
            self.brain.enhance_visual_prompt(
                f"{mood_prefix}, live news coverage {topic}, reporters with microphones, "
                f"outdoor broadcast van background"
            ),
            self.brain.enhance_visual_prompt(
                f"{mood_prefix}, data visualization about {topic} on large display, "
                f"modern news studio with blue ambient lighting"
            ),
            self.brain.enhance_visual_prompt(
                f"{mood_prefix}, news anchor presenting {topic} on green screen studio, "
                f"professional broadcast equipment visible"
            ),
            self.brain.enhance_visual_prompt(
                f"{mood_prefix}, global news coverage {topic}, world map background in "
                f"news studio, breaking news banner"
            ),
        ]

        visuals = []
        negative = self.brain.get_negative_prompt()
        quality = self.brain.get_quality_params(duration)

        for i in range(visual_count):
            if progress_cb:
                progress_cb({"type": "progress",
                             "text": f"Generating visual {i+1}/{visual_count}..."})
            try:
                prompt = prompts[i % len(prompts)]
                workflow = self._build_t2i_workflow(
                    prompt, negative, quality["steps"], quality["cfg"]
                )
                result = self.comfy.execute_pipeline(workflow, wait=True)
                if result["output_files"]:
                    out = result["output_files"][0]
                    data = self.comfy.download_output(out)
                    save_path = OUTPUT_DIR / f"visual_{i}_{int(time.time())}.png"
                    with open(save_path, "wb") as f:
                        f.write(data)
                    visuals.append(str(save_path))
            except Exception as e:
                logger.warning("Visual %d generation failed: %s", i, e)
                if progress_cb:
                    progress_cb({"type": "error",
                                 "text": f"Visual {i+1} failed: {e}"})

        if not visuals:
            visuals = [str(OUTPUT_DIR / "fallback_bg.png")]
            if not os.path.exists(visuals[0]):
                from moviepy import ColorClip
                from PIL import Image
                fallback = Image.new("RGB", (1024, 1024), (10, 20, 40))
                fallback.save(visuals[0])

        return self._cycle_visuals(visuals, duration)

    def _cycle_visuals(self, visuals: list[str], duration: int) -> list[str]:
        seg_count = max(1, math.ceil(duration / 15))
        if len(visuals) >= seg_count:
            return visuals[:seg_count]
        cycled = []
        for i in range(seg_count):
            cycled.append(visuals[i % len(visuals)])
        return cycled

    def _create_avatar(self, anchor_image: Optional[str],
                       audio_path: str,
                       progress_cb=None) -> str:
        if not anchor_image or not os.path.exists(anchor_image):
            return ""

        # Try LivePortrait first
        try:
            img_name = self.comfy.upload_image(anchor_image)
            audio_name = self.comfy.upload_audio(audio_path)
            workflow = self._build_talking_head_workflow(img_name, audio_name)
            result = self.comfy.execute_pipeline(workflow, wait=True,
                                                  progress_callback=progress_cb)
            if result["output_files"]:
                out = result["output_files"][0]
                data = self.comfy.download_output(out)
                save_path = OUTPUT_DIR / f"avatar_{int(time.time())}.mp4"
                with open(save_path, "wb") as f:
                    f.write(data)
                return str(save_path)
        except Exception as e:
            logger.warning("LivePortrait failed: %s, using static fallback", e)
            if progress_cb:
                progress_cb({"type": "error",
                             "text": f"LivePortrait failed ({e}), using static image as fallback"})

        # Fallback: return anchor image path for static overlay
        return anchor_image

    def _compose_video(self, avatar_path: str,
                       visuals: list[str],
                       audio_path: str,
                       script: dict,
                       full_text: str,
                       language: str,
                       mood: str = None,
                       progress_cb=None) -> str:
        from moviepy import (
            VideoFileClip, AudioFileClip, ImageClip, TextClip,
            CompositeVideoClip, ColorClip, concatenate_videoclips,
        )

        audio = AudioFileClip(audio_path)
        duration = audio.duration
        res_w, res_h = 1080, 1920

        avatar_layer = None
        if avatar_path and os.path.exists(avatar_path):
            ext = os.path.splitext(avatar_path)[1].lower()
            if ext == ".mp4":
                avatar_clip = VideoFileClip(avatar_path)
                avatar_w = int(res_w * 0.35)
                avatar_h = int(avatar_w * avatar_clip.h / avatar_clip.w)
                avatar_layer = (avatar_clip
                                .resized(width=avatar_w, height=avatar_h)
                                .with_position((res_w - avatar_w - 40,
                                                res_h - avatar_h - 180))
                                .with_duration(min(duration, avatar_clip.duration)))
            else:
                avatar_layer = (ImageClip(avatar_path)
                                .resized(height=int(res_h * 0.4))
                                .with_position((res_w - int(res_w * 0.35) - 40,
                                                res_h - int(res_h * 0.45)))
                                .with_duration(duration))

        theme = MOOD_THEMES.get(mood or DEFAULT_MOOD, MOOD_THEMES[DEFAULT_MOOD])

        background_layers = []
        total_visuals = max(1, len(visuals))
        visual_duration = duration / total_visuals
        overlay_opacity = theme["overlay_opacity"]
        crossfade_dur = 0.5
        ken_burns_zoom = 1.08

        for i, v_path in enumerate(visuals):
            start = i * visual_duration
            try:
                zoom_in = lambda t: 1 + (ken_burns_zoom - 1) * (t / visual_duration)
                img_clip = ImageClip(v_path)
                img = (img_clip
                       .resized(width=res_w * ken_burns_zoom, height=res_h * ken_burns_zoom)
                       .with_duration(visual_duration + crossfade_dur)
                       .with_start(start)
                       .with_position(lambda t: (
                           -(res_w * (ken_burns_zoom - 1) * t / visual_duration) / 2,
                           -(res_h * (ken_burns_zoom - 1) * t / visual_duration) / 2
                       )))
                if i > 0:
                    img = img.with_crossfadein(crossfade_dur)
                background_layers.append(img)

                dark = (ColorClip(size=(res_w, res_h), color=(0, 0, 0))
                        .with_opacity(overlay_opacity)
                        .with_duration(visual_duration + crossfade_dur)
                        .with_start(start))
                if i > 0:
                    dark = dark.with_crossfadein(crossfade_dur)
                background_layers.append(dark)
            except Exception as e:
                logger.debug("Skipped visual %d: %s", i, e)

        if not background_layers:
            bg = ColorClip(size=(res_w, res_h), color=(10, 20, 40))
            bg = bg.with_duration(duration)
            background_layers.append(bg)

        # News ticker at bottom (mood-colored)
        ticker_bg = (ColorClip(size=(res_w, 50), color=theme["ticker_bg"])
                     .with_opacity(0.9)
                     .with_position((0, res_h - 50))
                     .with_duration(duration))
        headline = script.get("headline", "BREAKING NEWS").upper()
        ticker_text = (TextClip(
            text=f"  {headline}  |  SAGARWAVE NEWS STUDIO  |  "
                 f"LATEST UPDATES  |  STAY INFORMED  ",
            font="Arial", font_size=24, color="white",
            bold=True, method="label",
        ).with_position((res_w // 4, res_h - 42))
         .with_duration(duration))

        # Lower third overlay (mood-colored)
        lt_bg = (ColorClip(size=(res_w, 90), color=theme["lower_third_bg"])
                 .with_opacity(0.85)
                 .with_position((0, res_h - 240))
                 .with_duration(duration))
        gold_bar = (ColorClip(size=(6, 90), color=theme["gold_bar"])
                    .with_position((0, res_h - 240))
                    .with_duration(duration))

        lt_text = (TextClip(
            text="SAGARWAVE NEWS STUDIO",
            font="Arial", font_size=30, color=theme["brand_color"],
            bold=True, method="label",
        ).with_position((20, res_h - 225))
         .with_duration(duration))
        lt_sub = (TextClip(
            text=script.get("introduction", language)[:80],
            font="Arial", font_size=22, color=theme["lower_third_text"],
            method="label",
        ).with_position((20, res_h - 190))
         .with_duration(duration))

        all_clips = background_layers + [
            lt_bg, gold_bar, lt_text, lt_sub,
            ticker_bg, ticker_text,
        ]

        if avatar_layer:
            all_clips.append(avatar_layer)

        # Subtitles (mood-styled)
        words = full_text.split()
        words_per_seg = max(1, int(len(words) / max(1, (duration / 3))))
        sub_color = theme["subtitle_color"]
        sub_stroke = theme["subtitle_stroke"]
        for i in range(0, len(words), words_per_seg):
            seg = " ".join(words[i:i + words_per_seg])
            if not seg:
                continue
            seg_start = i / max(1, len(words)) * duration
            seg_end = (i + words_per_seg) / max(1, len(words)) * duration
            txt = (TextClip(text=seg, font="Arial", font_size=26,
                            color=sub_color, stroke_color=sub_stroke,
                            stroke_width=2, method="label")
                   .with_position(("center", res_h - 120))
                   .with_start(seg_start)
                   .with_duration(min(seg_end - seg_start, 6)))
            all_clips.append(txt)

        final = CompositeVideoClip(all_clips, size=(res_w, res_h))
        final = final.with_audio(audio)

        out_path = str(OUTPUT_DIR / f"sagarwave_news_{int(time.time())}.mp4")
        final.write_videofile(out_path, codec="libx264",
                              audio_codec="aac", fps=30, logger=None,
                              preset="slow", bitrate="12000k",
                              ffmpeg_params=["-crf", "18", "-profile:v", "high", "-pix_fmt", "yuv420p"])
        audio.close()
        if avatar_layer and hasattr(avatar_layer, 'close'):
            avatar_layer.close()
        return out_path

    def _build_t2i_workflow(self, prompt: str, negative_prompt: str = "",
                            steps: int = 30, cfg: float = 7.5) -> dict:
        return {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": int(time.time()),
                    "steps": steps, "cfg": cfg,
                    "sampler_name": "dpmpp_2m",
                    "scheduler": "karras",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                }
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": 1024, "height": 1024, "batch_size": 1}
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": prompt, "clip": ["4", 1]}
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": negative_prompt or "text, watermark, low quality, blurry, distorted",
                    "clip": ["4", 1]
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["3", 0], "vae": ["4", 2]}
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "sagarwave_visual",
                           "images": ["8", 0]}
            },
        }

    def _build_talking_head_workflow(self, image_name: str,
                                      audio_name: str) -> dict:
        return {
            "1": {
                "class_type": "LoadImage",
                "inputs": {"image": image_name}
            },
            "2": {
                "class_type": "LoadAudio",
                "inputs": {"audio": audio_name}
            },
            "3": {
                "class_type": "LivePortrait",
                "inputs": {
                    "image": ["1", 0],
                    "audio": ["2", 0],
                    "face_scale": 1.0,
                    "face_offset_x": 0,
                    "face_offset_y": 0,
                }
            },
            "4": {
                "class_type": "VHS_VideoCombine",
                "inputs": {
                    "images": ["3", 0],
                    "frame_rate": 30,
                    "loop_count": 1,
                    "filename_prefix": "sagarwave_avatar",
                }
            },
            "5": {
                "class_type": "SaveVideo",
                "inputs": {
                    "video": ["4", 0],
                    "filename_prefix": "sagarwave_avatar_final",
                }
            },
        }

    def _build_animatediff_workflow(self, prompt: str, negative_prompt: str = "",
                                     steps: int = 25, cfg: float = 7.0,
                                     width: int = 1024, height: int = 1024,
                                     frame_count: int = 16) -> dict:
        return {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "Realistic_Vision_V6.0_NV_B1.safetensors"}
            },
            "2": {
                "class_type": "ADE_LoadAnimateDiffModel",
                "inputs": {"model_name": "mm_sd_v15_v2.ckpt"}
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": prompt, "clip": ["1", 1]}
            },
            "4": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": negative_prompt or "text, watermark, low quality, blurry, distorted, ugly",
                           "clip": ["1", 1]}
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": width, "height": height, "batch_size": frame_count}
            },
            "6": {
                "class_type": "ADE_AnimateDiffLoaderWithContext",
                "inputs": {
                    "model": ["2", 0],
                    "latents": ["5", 0],
                    "context_options": ["7", 0],
                }
            },
            "7": {
                "class_type": "ADE_StandardStaticContextOptions",
                "inputs": {}
            },
            "8": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": int(time.time()), "steps": steps, "cfg": cfg,
                    "sampler_name": "dpmpp_2m", "scheduler": "karras",
                    "denoise": 1.0,
                    "model": ["6", 0],
                    "positive": ["3", 0],
                    "negative": ["4", 0],
                    "latent_image": ["5", 0],
                }
            },
            "9": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["8", 0], "vae": ["1", 2]}
            },
            "10": {
                "class_type": "VHS_VideoCombine",
                "inputs": {
                    "images": ["9", 0],
                    "frame_rate": 8,
                    "loop_count": 1,
                    "filename_prefix": "animatediff_background",
                }
            },
            "11": {
                "class_type": "SaveVideo",
                "inputs": {
                    "video": ["10", 0],
                    "filename_prefix": "animatediff_output",
                }
            },
        }

    def generate_i2v_video(
        self,
        image_path: str,
        audio_path: str,
        topic: str = "",
        mood: str = None,
        progress_callback: Optional[Callable] = None,
    ) -> dict:
        self.mood = mood if mood and mood in MOOD_THEMES else self.mood
        self.pipeline_state = {
            "id": str(int(time.time())),
            "status": "running",
            "mood": self.mood,
            "steps": [], "current_step": 0,
            "outputs": [], "error": None,
        }
        theme = self._get_theme()
        mood_prefix = theme["visual_prefix"]

        try:
            self._report(progress_callback, 1, 4, "Uploading image to ComfyUI...")
            img_name = self.comfy.upload_image(image_path)

            self._report(progress_callback, 2, 4, "Uploading audio to ComfyUI...")
            audio_name = self.comfy.upload_audio(audio_path)

            self._report(progress_callback, 3, 4, "Generating talking head with LivePortrait...")
            head_workflow = self._build_talking_head_workflow(img_name, audio_name)
            head_result = self.comfy.execute_pipeline(head_workflow, wait=True, progress_callback=progress_callback)

            avatar_video = None
            if head_result.get("output_files"):
                out = head_result["output_files"][0]
                data = self.comfy.download_output(out)
                avatar_video = str(OUTPUT_DIR / f"i2v_avatar_{int(time.time())}.mp4")
                with open(avatar_video, "wb") as f:
                    f.write(data)

            self._report(progress_callback, 4, 4, "Composing final professional video...")
            output = self._compose_video(
                avatar_video, [image_path], audio_path,
                {"headline": topic.upper() if topic else "SAGARWAVE NEWS",
                 "introduction": "", "language": "English"},
                topic or "", "English", self.mood, progress_callback,
            )

            self.pipeline_state["status"] = "completed"
            self.pipeline_state["outputs"].append(output)
            self._report(progress_callback, 4, 4, f"Done! Output: {output}")

        except Exception as e:
            logger.error("I2V pipeline failed: %s", e)
            self.pipeline_state["status"] = "failed"
            self.pipeline_state["error"] = str(e)
            self._report(progress_callback, 0, 0, f"Error: {e}")

        return self.pipeline_state

    def execute_auto_news_from_audio(
        self,
        image_path: str,
        audio_path: str,
        progress_callback: Optional[Callable] = None,
    ) -> dict:
        self.pipeline_state = {
            "id": str(int(time.time())),
            "status": "running",
            "steps": [], "current_step": 0,
            "outputs": [], "error": None,
        }

        try:
            self._report(progress_callback, 1, 6, "Transcribing audio and detecting topic...")
            info = extract_topic_from_audio(audio_path)
            topic = info.get("topic", "general news")
            detected_lang = info.get("language", "English")
            summary = info.get("summary", "")
            transcript = info.get("full_transcript", "")
            self.pipeline_state["detected_topic"] = topic
            self.pipeline_state["detected_language"] = detected_lang

            self._report(progress_callback, 2, 6, f"Detected: {topic} ({detected_lang})")

            self._report(progress_callback, 3, 6, f"Generating news script in {detected_lang}...")
            script = self.brain.generate_news_script(topic, detected_lang, 60)
            full_text = script.get("full_text") or self._assemble_script(script)
            self.pipeline_state["script"] = script

            self._report(progress_callback, 4, 6, "Detecting mood from audio...")
            mood_result = detect_mood(audio_path, topic)
            self.mood = mood_result.get("mood", DEFAULT_MOOD)
            self.pipeline_state["mood"] = self.mood
            theme = self._get_theme()

            self._report(progress_callback, 5, 6, "Uploading to ComfyUI and generating talking head...")
            img_name = self.comfy.upload_image(image_path)
            audio_name = self.comfy.upload_audio(audio_path)
            head_workflow = self._build_talking_head_workflow(img_name, audio_name)
            head_result = self.comfy.execute_pipeline(
                head_workflow, wait=True, progress_callback=progress_callback
            )

            avatar_video = None
            if head_result.get("output_files"):
                out = head_result["output_files"][0]
                data = self.comfy.download_output(out)
                avatar_video = str(OUTPUT_DIR / f"auto_avatar_{int(time.time())}.mp4")
                with open(avatar_video, "wb") as f:
                    f.write(data)

            self._report(progress_callback, 6, 6,
                         f"Composing final {detected_lang} news video ({MOOD_THEMES.get(self.mood, MOOD_THEMES[DEFAULT_MOOD])['name']} mood)...")

            news_images = [image_path]
            if summary:
                from agent_core import PROFESSIONAL_ENHANCEMENTS
                prefix = PROFESSIONAL_ENHANCEMENTS["visual_prompt_prefix"]
                visual_prompt = f"{prefix}, {topic}, news studio, professional broadcast"
                t2i_wf = self._build_t2i_workflow(visual_prompt, steps=25, cfg=7.0)
                try:
                    t2i_result = self.comfy.execute_pipeline(t2i_wf, wait=True)
                    if t2i_result.get("output_files"):
                        out2 = t2i_result["output_files"][0]
                        data2 = self.comfy.download_output(out2)
                        bg_img = str(OUTPUT_DIR / f"auto_bg_{int(time.time())}.png")
                        with open(bg_img, "wb") as f:
                            f.write(data2)
                        news_images.append(bg_img)
                except Exception as e:
                    logger.debug("T2I background generation failed: %s", e)

            output = self._compose_video(
                avatar_video, news_images, audio_path,
                script, full_text, detected_lang,
                self.mood, progress_callback,
            )

            self.pipeline_state["status"] = "completed"
            self.pipeline_state["outputs"].append(output)
            self._report(progress_callback, 6, 6, f"Done! Output: {output}")

        except Exception as e:
            logger.error("Auto news pipeline failed: %s", e)
            self.pipeline_state["status"] = "failed"
            self.pipeline_state["error"] = str(e)
            self._report(progress_callback, 0, 0, f"Error: {e}")

        return self.pipeline_state

    def _report(self, cb, step: int, total: int, text: str):
        if cb:
            cb({"type": "pipeline", "step": step,
                "total": total, "text": text})

    def _assemble_script(self, script: dict) -> str:
        parts = [
            script.get("headline", ""),
            script.get("introduction", ""),
            script.get("main_story", ""),
        ]
        highlights = script.get("highlights", [])
        if highlights:
            parts.append(" ".join(highlights))
        parts.append(script.get("conclusion", ""))
        return " ".join(p for p in parts if p)
