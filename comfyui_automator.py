import os
import json
import asyncio
import time
import uuid
from pathlib import Path
from typing import Optional
import httpx


class ComfyUIAutomator:
    def __init__(self, base_url: str = "http://127.0.0.1:8188"):
        self.base_url = base_url.rstrip("/")
        self.client_id = str(uuid.uuid4())
        self.ws_url = (
            self.base_url.replace("http://", "ws://")
            .replace("https://", "wss://")
            + "/ws?clientId=" + self.client_id
        )

    # ─── Health ──────────────────────────────────────────
    def is_online(self) -> bool:
        try:
            r = httpx.get(f"{self.base_url}/system_stats", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def get_system_stats(self) -> dict:
        r = httpx.get(f"{self.base_url}/system_stats", timeout=5)
        r.raise_for_status()
        return r.json()

    # ─── Queue ───────────────────────────────────────────
    def queue_prompt(self, workflow: dict) -> str:
        payload = {"prompt": workflow, "client_id": self.client_id}
        r = httpx.post(f"{self.base_url}/prompt", json=payload, timeout=30)
        r.raise_for_status()
        return r.json().get("prompt_id", "")

    def get_queue(self) -> dict:
        r = httpx.get(f"{self.base_url}/queue", timeout=10)
        r.raise_for_status()
        return r.json()

    def get_history(self, prompt_id: str = "") -> dict:
        params = {"max_items": 200}
        if prompt_id:
            r = httpx.get(f"{self.base_url}/history/{prompt_id}", timeout=10)
        else:
            r = httpx.get(f"{self.base_url}/history", params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    # ─── Uploads ─────────────────────────────────────────
    def upload_image(self, file_path: str | Path,
                     filename: Optional[str] = None,
                     image_type: str = "input",
                     subfolder: str = "") -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"{path} not found")
        name = filename or path.name
        with open(path, "rb") as f:
            files = {"image": (name, f, "image/png")}
            data = {"type": image_type, "overwrite": "true", "subfolder": subfolder}
            r = httpx.post(f"{self.base_url}/upload/image",
                           files=files, data=data, timeout=60)
            r.raise_for_status()
        return r.json().get("name", name)

    def upload_audio(self, file_path: str | Path,
                     filename: Optional[str] = None) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"{path} not found")
        name = filename or path.name
        with open(path, "rb") as f:
            files = {"file": (name, f, "audio/wav")}
            r = httpx.post(f"{self.base_url}/upload/audio",
                           files=files, timeout=120)
            r.raise_for_status()
        return r.json().get("name", name)

    # ─── WebSocket Progress ──────────────────────────────
    def listen_for_progress(self, prompt_id: str,
                            timeout: int = 600) -> dict:
        import asyncio
        import websockets

        async def _listen():
            async with websockets.connect(self.ws_url) as ws:
                while True:
                    msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
                    data = json.loads(msg)
                    msg_type = data.get("type", "")

                    if msg_type == "progress":
                        yield {
                            "type": "progress",
                            "node": data["data"].get("node", ""),
                            "step": data["data"].get("step", 0),
                            "max": data["data"].get("max", 0),
                            "node_name": data["data"].get("node_name", ""),
                        }
                    elif msg_type == "executing":
                        node = data["data"].get("node", None)
                        if node is None:
                            yield {"type": "complete"}
                            return
                        yield {"type": "executing", "node": node}
                    elif msg_type == "executed":
                        yield {
                            "type": "executed",
                            "node": data["data"].get("node", ""),
                        }
                    elif msg_type == "execution_error":
                        yield {
                            "type": "error",
                            "error": data["data"].get("error", {}),
                        }
                        return

        async def run():
            results = []
            async for event in _listen():
                results.append(event)
                if event["type"] in ("complete", "error"):
                    break
            return results

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(run())
        finally:
            loop.close()

    def wait_for_completion(self, prompt_id: str,
                            poll_interval: float = 2.0,
                            timeout: int = 600) -> dict:
        start = time.time()
        while time.time() - start < timeout:
            try:
                history = self.get_history(prompt_id)
                if prompt_id in history:
                    return history[prompt_id]
            except Exception:
                pass
            time.sleep(poll_interval)
        raise TimeoutError(f"Prompt {prompt_id} did not complete")

    # ─── Workflow Management ─────────────────────────────
    def load_workflow(self, path: str | Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "prompt" in data:
            return data["prompt"]
        return data

    def save_workflow(self, workflow: dict, name: str) -> str:
        dest = Path("workflow_templates") / f"{name}.json"
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(workflow, f, indent=2)
        return str(dest)

    def update_workflow_node(self, workflow: dict, node_id: str,
                             field_path: str, value) -> dict:
        parts = field_path.split(".")
        target = workflow.get(node_id, {}).get("inputs", {})
        for p in parts[:-1]:
            target = target.setdefault(p, {})
        target[parts[-1]] = value
        return workflow

    def get_node_inputs(self, workflow: dict, node_id: str) -> dict:
        return workflow.get(node_id, {}).get("inputs", {})

    def get_output_filenames(self, history_result: dict) -> list[str]:
        filenames = []
        outputs = history_result.get("outputs", {})
        for node_id, node_output in outputs.items():
            for output_type, output_list in node_output.items():
                for item in output_list:
                    if isinstance(item, dict):
                        fname = item.get("filename", "")
                        if fname:
                            filenames.append(
                                os.path.join(
                                    item.get("subfolder", ""), fname
                                )
                            )
        return filenames

    def download_output(self, filename: str) -> bytes:
        r = httpx.get(
            f"{self.base_url}/view",
            params={"filename": os.path.basename(filename),
                    "subfolder": os.path.dirname(filename),
                    "type": "output"},
            timeout=30,
        )
        r.raise_for_status()
        return r.content

    # ─── Node Discovery ─────────────────────────────────
    def get_object_info(self) -> dict:
        r = httpx.get(f"{self.base_url}/object_info", timeout=15)
        r.raise_for_status()
        return r.json()

    def get_available_node_types(self) -> list[str]:
        info = self.get_object_info()
        return sorted(info.keys())

    def get_node_spec(self, class_type: str) -> dict:
        info = self.get_object_info()
        return info.get(class_type, {})

    def get_model_folders(self) -> list[str]:
        try:
            r = httpx.get(f"{self.base_url}/folder_paths", timeout=10)
            r.raise_for_status()
            return list(r.json().keys())
        except Exception:
            return ["checkpoints", "loras", "vae", "controlnet",
                    "embeddings", "clip", "upscale_models", "ipadapter"]

    def get_available_models(self, folder: str = "checkpoints") -> list[str]:
        try:
            r = httpx.get(f"{self.base_url}/folder_paths",
                          params={"folder": folder}, timeout=10)
            r.raise_for_status()
            models = r.json()
            if isinstance(models, list):
                return models
            if isinstance(models, dict):
                for key in (folder, "models", "files"):
                    if key in models:
                        return models[key]
            return []
        except Exception:
            return []

    def get_all_models(self) -> dict:
        folders = self.get_model_folders()
        result = {}
        for folder in folders:
            try:
                models = self.get_available_models(folder)
                if models:
                    result[folder] = models
            except Exception:
                pass
        return result

    # ─── Model Download ─────────────────────────────────
    def download_model(self, url: str, folder: str = "checkpoints",
                       filename: Optional[str] = None,
                       progress_callback=None) -> str:
        import httpx as httpx_client
        filename = filename or url.split("/")[-1].split("?")[0]
        dest_dir = self._get_model_path(folder)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / filename

        if dest.exists():
            if progress_callback:
                progress_callback({"type": "progress",
                                   "text": f"Already exists: {filename}"})
            return str(dest)

        if progress_callback:
            progress_callback({"type": "progress",
                               "text": f"Downloading {filename}..."})

        with httpx_client.stream("GET", url, timeout=3600,
                                 follow_redirects=True) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with open(dest, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total > 0:
                        pct = int(downloaded / total * 100)
                        progress_callback({"type": "progress",
                                           "text": f"Downloading {filename}: {pct}%",
                                           "percent": pct})

        if progress_callback:
            progress_callback({"type": "progress",
                               "text": f"Downloaded {filename}"})
        return str(dest)

    def _get_model_path(self, folder: str) -> Path:
        from config import COMFYUI_MODELS
        return COMFYUI_MODELS / folder

    # ─── Direct Pipeline Execution ───────────────────────
    def execute_pipeline(self, workflow: dict,
                         wait: bool = True,
                         progress_callback=None) -> dict:
        prompt_id = self.queue_prompt(workflow)
        result = {"prompt_id": prompt_id, "status": "queued"}

        if progress_callback:
            progress_callback({"type": "queued", "prompt_id": prompt_id})

        if wait:
            events = self.listen_for_progress(prompt_id)
            for event in events:
                if progress_callback:
                    progress_callback(event)
            history = self.wait_for_completion(prompt_id)
            files = self.get_output_filenames(history)
            result.update({
                "status": "completed",
                "history": history,
                "output_files": files,
            })
        return result
