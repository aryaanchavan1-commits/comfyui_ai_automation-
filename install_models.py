"""Resumable model downloader with live progress"""
import sys, os, time, zipfile, io, warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import COMFYUI_BASE, HF_TOKEN

# Suppress noisy huggingface_hub warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

models_dir = COMFYUI_BASE / "models"

downloads = [
    {
        "name": "SDXL base 1.0 (6.9 GB)",
        "folder": "checkpoints",
        "url": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors",
        "filename": "sd_xl_base_1.0.safetensors",
    },
    {
        "name": "SDXL VAE (335 MB)",
        "folder": "vae",
        "url": "https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors",
        "filename": "sdxl_vae.safetensors",
    },
    {
        "name": "4x-UltraSharp (67 MB)",
        "folder": "upscale_models",
        "url": "https://huggingface.co/lokCX/4x-Ultrasharp/resolve/main/4x-UltraSharp.pth",
        "filename": "4x-UltraSharp.pth",
    },
    {
        "name": "Flux.1 Dev (23 GB) - Video Model",
        "folder": "diffusion_models",
        "hf_repo": "black-forest-labs/FLUX.1-dev",
        "hf_file": "flux1-dev.safetensors",
        "filename": "flux1-dev.safetensors",
        "need_token": True,
    },
    {
        "name": "InsightFace buffalo_l (face detection)",
        "folder": "insightface",
        "url": "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip",
        "filename": "buffalo_l",
        "is_zip": True,
    },
    {
        "name": "SDXL Detail Enhancer LoRA (add-detail-xl)",
        "folder": "loras",
        "hf_repo": "LyliaEngine/add-detail-xl",
        "hf_file": "add-detail-xl.safetensors",
        "filename": "add-detail-xl.safetensors",
    },
]

import httpx

def _show_progress(downloaded, total, start):
    if total <= 0:
        return
    elapsed = time.time() - start
    speed = downloaded / elapsed / 1e6 if elapsed > 0 else 0
    pct = downloaded / total * 100
    bar = "#" * int(pct / 5) + "." * (20 - int(pct / 5))
    eta = (total - downloaded) / max(downloaded / elapsed, 0.01) if elapsed > 0 else 0
    print(f"\r  [{bar}] {pct:.0f}% - {downloaded/1e6:.0f}/{total/1e6:.0f} MB - {speed:.0f} MB/s - {eta:.0f}s left", end="", flush=True)

def httpx_download(url, dest, headers=None, is_zip=False, extract_dir=None):
    with httpx.Client(timeout=httpx.Timeout(7200.0, connect=30.0)) as client:
        with client.stream("GET", url, follow_redirects=True, headers=headers or {}) as resp:
            if resp.status_code == 401:
                print(f"\r  [FAIL] Authentication required (401)")
                return False
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            start = time.time()

            if is_zip:
                chunks = []
                for chunk in resp.iter_bytes(chunk_size=65536):
                    chunks.append(chunk)
                    downloaded += len(chunk)
                    _show_progress(downloaded, total, start)
                data = b"".join(chunks)
                print(f"\r  Extracting zip...                      ")
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    zf.extractall(extract_dir)
                print(f"\r  [OK] Extracted to {extract_dir}")
            else:
                with open(dest, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=65536):
                        f.write(chunk)
                        downloaded += len(chunk)
                        _show_progress(downloaded, total, start)
                sz = dest.stat().st_size / 1e6
                print(f"\r  [OK] Done! ({sz:.0f} MB)              ")
    return True

def hf_download_with_progress(repo_id, filename, dest, token=None, is_zip=False, extract_dir=None):
    """Download from HF Hub using authenticated session + httpx progress."""
    import requests as req_lib
    session = req_lib.Session()
    if token:
        session.headers.update({"Authorization": f"Bearer {token}"})
    url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
    # First HEAD to follow redirects and get the real CDN URL
    head = session.get(url, stream=True, timeout=30)
    if head.status_code == 401:
        print(f"\r  [FAIL] Authentication required (401)")
        return False
    if head.status_code == 403:
        print(f"\r  [FAIL] Access forbidden. You may need to accept the license:")
        print(f"         https://huggingface.co/{repo_id}")
        return False
    head.raise_for_status()
    cdn_url = head.url

    # Download from CDN URL with httpx for progress
    if is_zip:
        return httpx_download(cdn_url, None, headers=None, is_zip=True, extract_dir=extract_dir)
    else:
        return httpx_download(cdn_url, dest)

for dl in downloads:
    name = dl["name"]
    folder = dl["folder"]
    is_zip = dl.get("is_zip", False)

    dest = models_dir / folder / dl["filename"]

    # Check if already exists
    if is_zip:
        dest_dir = dest
        expected_file = dest_dir / "det_10g.onnx"
        if expected_file.exists():
            print(f"[OK] {name} already exists")
            continue
    else:
        if dest.exists() and dest.stat().st_size > 1_000_000:
            sz = dest.stat().st_size / 1e9
            unit = "GB" if sz > 1 else "MB"
            val = sz if sz > 1 else dest.stat().st_size / 1e6
            print(f"[OK] {name} already exists ({val:.1f} {unit})")
            continue

    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"\n--- {name} ---")

    # Try HF Hub download
    hf_repo = dl.get("hf_repo")
    if hf_repo:
        hf_token = HF_TOKEN or None
        success = hf_download_with_progress(
            hf_repo, dl["hf_file"], dest,
            token=hf_token,
            is_zip=is_zip,
            extract_dir=dest if is_zip else None,
        )
        if success:
            continue
        if not success and dl.get("url"):
            print(f"  Falling back to direct URL...")

    # Direct URL download (fallback)
    url = dl.get("url")
    if not url:
        print(f"  [SKIP] No URL available")
        continue

    headers = {}
    if dl.get("need_token") and HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    try:
        httpx_download(url, dest, headers, is_zip=is_zip, extract_dir=dest if is_zip else None)
    except Exception as e:
        print(f"\r  [FAIL] {str(e)[:100]}")
        if not is_zip and dest.exists():
            dest.unlink()

print("\n=== All downloads complete! ===")
