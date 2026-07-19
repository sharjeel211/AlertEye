"""
Model Downloader - Downloads pretrained models from various sources
"""

import os
import sys
import requests
import hashlib
from pathlib import Path
from typing import Optional, Callable
from utils.logger import get_logger

logger = get_logger("model_downloader")
if getattr(sys, 'frozen', False):
    PROJECT_ROOT = sys._MEIPASS
else:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")

MODEL_REGISTRY = {

    "weapon_detection": {
        "filename": "weapon_detection.pt",
        "description": "YOLOv8 Weapon Detection (guns, knives, rifles)",
        "source": "ultralytics_hub",
        "model_id": "yolov8n",
        "classes_note": "Uses YOLOv8 pretrained; specialized model loaded from HuggingFace",
        "hf_repo": "keremberke/yolov8-weapon-detection",
        "hf_file": "best.pt",
        "fallback": "yolov8n.pt"
    },

    "fire_smoke": {
        "filename": "fire_smoke.pt",
        "description": "YOLOv8 Fire and Smoke Detection",
        "source": "huggingface",
        "hf_repo": "arnabdhar/YOLOv8-Fire-Detection",
        "hf_file": "model.pt",
        "fallback": "yolov8n.pt"
    },

    "accident_detection": {
        "filename": "accident_detection.pt",
        "description": "YOLOv8 Accident/Collision Detection",
        "source": "ultralytics_hub",
        "model_id": "yolov8n",
        "fallback": "yolov8n.pt"
    },

    "general_yolov8n": {
        "filename": "yolov8n.pt",
        "description": "YOLOv8 Nano - General Object Detection",
        "source": "ultralytics_hub",
        "model_id": "yolov8n",
        "fallback": "yolov8n.pt"
    },

    "yolov8m": {
        "filename": "yolov8m.pt",
        "description": "YOLOv8 Medium - Higher accuracy detection",
        "source": "ultralytics_hub",
        "model_id": "yolov8m",
        "fallback": "yolov8m.pt"
    }
}

def ensure_models_dir():
    """Create models directory if it doesn't exist."""
    os.makedirs(MODELS_DIR, exist_ok=True)

def model_exists(filename: str) -> bool:
    """Check if a model file exists."""
    return os.path.exists(os.path.join(MODELS_DIR, filename))

def get_model_path(filename: str) -> str:
    """Return absolute path to a model file."""
    return os.path.join(MODELS_DIR, filename)

def download_model_ultralytics(model_id: str, dest_path: str,
                                progress_cb: Optional[Callable] = None) -> bool:
    """
    Download a model using Ultralytics auto-download.
    Ultralytics automatically downloads to ~/.ultralytics/assets/ 
    and we copy to our models dir.
    """
    try:
        from ultralytics import YOLO
        logger.info(f"Downloading {model_id} via Ultralytics...")
        model = YOLO(model_id)

        import torch
        src = model.ckpt_path if hasattr(model, "ckpt_path") else None
        if src and os.path.exists(src):
            import shutil
            shutil.copy2(src, dest_path)
        else:

            model.save(dest_path)
        logger.info(f"Saved {model_id} → {dest_path}")
        return True
    except Exception as e:
        logger.error(f"Ultralytics download failed for {model_id}: {e}")
        return False

def download_model_huggingface(repo: str, filename: str,
                                dest_path: str,
                                progress_cb: Optional[Callable] = None) -> bool:
    """Download a model from HuggingFace Hub."""
    try:
        from huggingface_hub import hf_hub_download
        logger.info(f"Downloading {filename} from HuggingFace {repo}...")
        local_path = hf_hub_download(repo_id=repo, filename=filename)
        import shutil
        shutil.copy2(local_path, dest_path)
        logger.info(f"Downloaded {repo}/{filename} → {dest_path}")
        return True
    except ImportError:
        logger.warning("huggingface_hub not installed. Falling back to ultralytics.")
        return False
    except Exception as e:
        logger.error(f"HuggingFace download failed for {repo}/{filename}: {e}")
        return False

def download_all_models(progress_cb: Optional[Callable] = None) -> dict:
    """
    Download all required models.
    Returns dict: {model_name: success_bool}
    """
    ensure_models_dir()
    results = {}

    required = [
        "general_yolov8n",
        "weapon_detection",
        "fire_smoke",
        "accident_detection"
    ]

    for i, model_name in enumerate(required):
        info = MODEL_REGISTRY.get(model_name)
        if not info:
            continue

        dest = os.path.join(MODELS_DIR, info["filename"])
        if os.path.exists(dest):
            logger.info(f"Model already exists: {info['filename']}")
            results[model_name] = True
            if progress_cb:
                progress_cb(model_name, i + 1, len(required), True)
            continue

        logger.info(f"Downloading model: {model_name} ─ {info['description']}")
        success = False

        if info.get("hf_repo") and info.get("hf_file"):
            success = download_model_huggingface(
                info["hf_repo"], info["hf_file"], dest, progress_cb
            )

        if not success and info.get("fallback"):
            success = download_model_ultralytics(info["fallback"], dest, progress_cb)

        results[model_name] = success
        if progress_cb:
            progress_cb(model_name, i + 1, len(required), success)

    return results

def get_best_model_path(module_name: str) -> str:
    """
    Return the path to the best available model for a module.
    Falls back to general YOLOv8n if specialized model missing.
    """
    info = MODEL_REGISTRY.get(module_name, {})
    primary = os.path.join(MODELS_DIR, info.get("filename", ""))
    if os.path.exists(primary):
        return primary

    fallback_file = info.get("fallback", "yolov8n.pt")
    fallback_path = os.path.join(MODELS_DIR, fallback_file)
    if os.path.exists(fallback_path):
        return fallback_path

    return info.get("model_id", "yolov8n")
