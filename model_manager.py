import os
import json
import re
import time
from pathlib import Path
from typing import Optional, Callable
from comfyui_automator import ComfyUIAutomator

MODEL_FOLDER_MAP = {
    "checkpoint": "checkpoints", "ckpt": "checkpoints",
    "safetensors": "checkpoints", "diffusion_model": "checkpoints",
    "lora": "loras", "lycoris": "loras",
    "vae": "vae", "vae_approx": "vae",
    "controlnet": "controlnet", "t2i_adapter": "controlnet",
    "embedding": "embeddings", "text_encoder": "embeddings",
    "clip": "clip", "clip_vision": "clip_vision",
    "upscaler": "upscale_models", "esrgan": "upscale_models",
    "ip_adapter": "ipadapter", "ipadapter": "ipadapter",
    "style_model": "style_models",
    "hypernetwork": "hypernetworks",
    "gligen": "gligen",
    "photorealism": "checkpoints",
    "flux": "checkpoints",
    "sdxl": "checkpoints",
    "sd15": "checkpoints",
    "sd21": "checkpoints",
    "animatediff": "animatediff_models",
    "video": "checkpoints",
    "liveportrait": "liveportrait",
    "insightface": "insightface",
    "sam": "sams",
    "groundingdino": "grounding-dino",
}

RECOMMENDED_MODELS = {
    "checkpoints": {
        "SDXL base 1.0": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors",
        "SDXL refiner 1.0": "https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/resolve/main/sd_xl_refiner_1.0.safetensors",
        "Flux.1 Dev": "https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/flux1-dev.safetensors",
        "Realistic Vision V6": "https://huggingface.co/SG161222/Realistic_Vision_V6.0_B1_noVAE/resolve/main/Realistic_Vision_V6.0_B1_noVAE.safetensors",
        "DreamShaper XL": "https://huggingface.co/Lykon/dreamshaper-xl-1-0/resolve/main/dreamshaperXL_10.safetensors",
    },
    "loras": {
        "SDXL - Detail Enhancer": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0_0.9vae.safetensors",
    },
    "vae": {
        "SDXL VAE": "https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors",
    },
}

MODEL_HINT_KEYWORDS = {
    "checkpoints": [
        "checkpoint", "model", "ckpt", "sd", "stable diffusion", "flux",
        "sdxl", "sd15", "realistic", "anime", "dreamshaper", "juggernaut",
    ],
    "loras": [
        "lora", "lycoris", "style", "character", "concept",
    ],
    "vae": ["vae", "variational"],
    "controlnet": ["controlnet", "canny", "depth", "pose", "openpose"],
    "embeddings": ["embedding", "textual inversion", "ti"],
}


class ModelManager:
    def __init__(self, comfy: ComfyUIAutomator):
        self.comfy = comfy

    def discover_folder(self, model_type: str) -> str:
        mt = model_type.lower().strip()
        for key, folder in MODEL_FOLDER_MAP.items():
            if key in mt:
                return folder
        return "checkpoints"

    def suggest_folder(self, model_name: str) -> str:
        mn = model_name.lower()
        for folder, keywords in MODEL_HINT_KEYWORDS.items():
            for kw in keywords:
                if kw in mn:
                    return folder
        return "checkpoints"

    def scan_installed_models(self) -> dict:
        return self.comfy.get_all_models()

    def is_model_installed(self, name_part: str, folder: str = "checkpoints") -> bool:
        models = self.comfy.get_available_models(folder)
        return any(name_part.lower() in m.lower() for m in models)

    def download_if_missing(self, model_name: str, folder: str,
                            url: Optional[str] = None,
                            progress_cb: Optional[Callable] = None) -> Optional[str]:
        models = self.comfy.get_available_models(folder)
        for m in models:
            if model_name.lower() in m.lower():
                if progress_cb:
                    progress_cb({"type": "progress",
                                 "text": f"Model found: {m}"})
                return None

        if not url:
            url = self._find_download_url(model_name, folder)

        if url:
            return self.comfy.download_model(url, folder, progress_callback=progress_cb)
        return None

    def auto_ensure_model(self, requirement: str,
                          progress_cb: Optional[Callable] = None) -> list[dict]:
        results = []
        req_lower = requirement.lower()

        needed = []
        if "flux" in req_lower:
            needed.append(("Flux.1 Dev", "checkpoints",
                           "https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/flux1-dev.safetensors"))
        if "sdxl" in req_lower or "xl" in req_lower:
            needed.append(("SDXL base", "checkpoints",
                           "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors"))
        if "realistic" in req_lower or "photo" in req_lower:
            needed.append(("Realistic Vision", "checkpoints",
                           "https://huggingface.co/SG161222/Realistic_Vision_V6.0_B1_noVAE/resolve/main/Realistic_Vision_V6.0_B1_noVAE.safetensors"))
        if "lora" in req_lower:
            needed.append(("Detail Enhancer", "loras",
                           "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0_0.9vae.safetensors"))
        if "vae" in req_lower:
            needed.append(("SDXL VAE", "vae",
                           "https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors"))

        if not needed:
            folder = "checkpoints"
            if "lora" in req_lower:
                folder = "loras"
            elif "vae" in req_lower:
                folder = "vae"
            needed.append((requirement[:40], folder, None))

        for name, folder, url in needed:
            result = self.download_if_missing(name, folder, url, progress_cb)
            results.append({
                "name": name,
                "folder": folder,
                "action": "downloaded" if result else "already_installed",
                "path": result or "",
            })

        return results

    def _find_download_url(self, model_name: str, folder: str) -> Optional[str]:
        models = RECOMMENDED_MODELS.get(folder, {})
        for name, url in models.items():
            if model_name.lower() in name.lower():
                return url
        check_name = model_name.lower().replace(" ", "_").replace("-", "_")
        return f"https://huggingface.co/{check_name}/{check_name}/resolve/main/{check_name}.safetensors"
