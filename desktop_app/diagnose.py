"""
AlertEye environment diagnostic.
Run on BOTH PCs and compare the output line-by-line:
    python diagnose.py
The two outputs MUST match. Any difference = your false-detection cause.
"""
import os, sys, hashlib

ROOT = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(ROOT, "models")

def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

print("=" * 60)
print("PYTHON :", sys.version.split()[0], "(", sys.executable, ")")

for mod in ("ultralytics", "torch", "torchvision", "cv2", "numpy", "PIL"):
    try:
        m = __import__(mod)
        v = getattr(m, "__version__", "?")
        print(f"{mod:12}: {v}")
    except Exception as e:
        print(f"{mod:12}: NOT INSTALLED ({e})")

try:
    import torch
    print("CUDA avail :", torch.cuda.is_available())
except Exception:
    pass

print("=" * 60)
print("MODEL FILES (size + md5 must be IDENTICAL on both PCs):")
for name in ("weapon_detection.pt", "fire_smoke.pt",
             "accident_detection.pt", "yolov8n.pt"):
    p = os.path.join(MODELS, name)
    if os.path.exists(p):
        print(f"  {name:24} {os.path.getsize(p):>12,} bytes  {md5(p)}")
    else:
        print(f"  {name:24} *** MISSING ***")

print("=" * 60)
print("WHAT EACH DETECTOR ACTUALLY LOADS:")
sys.path.insert(0, ROOT)
try:
    from utils.model_downloader import get_best_model_path
    from ultralytics import YOLO
    for module in ("weapon_detection", "fire_smoke", "accident_detection"):
        path = get_best_model_path(module)
        is_fallback = path.endswith("yolov8n.pt") or not path.endswith(".pt") \
            or os.path.basename(path) != {
                "weapon_detection": "weapon_detection.pt",
                "fire_smoke": "fire_smoke.pt",
                "accident_detection": "accident_detection.pt",
            }[module]
        flag = "  <-- !!! WRONG MODEL (COCO FALLBACK) !!!" if is_fallback else ""
        try:
            names = list(YOLO(path).names.values())
        except Exception as e:
            names = f"LOAD FAILED: {e}"
        print(f"  {module:20} -> {os.path.basename(path)}{flag}")
        print(f"      classes: {names}")
except Exception as e:
    print("  detector import failed:", e)
print("=" * 60)
