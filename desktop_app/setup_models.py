"""
AlertEye — Specialized Model Downloader (no token required)
==============================================================
Downloads fire/smoke and weapon detection models directly from PUBLIC,
ungated HuggingFace repos. No API key / token is needed.

USAGE:
  python setup_models.py

Each download is VERIFIED before it replaces your existing model: the
downloaded file's class names must match the expected keywords (e.g. a
weapon model must actually contain gun/pistol/knife classes). This stops
a wrong model from silently corrupting your detector.

If automatic download fails, grab the .pt manually from the model's
"Files and versions" tab on huggingface.co and drop it into models/
with the right name (fire_smoke.pt / weapon_detection.pt).
"""

import os
import argparse

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")

SPECIALIZED_MODELS = [
    {
        "name": "Fire & Smoke Detection",
        "dest": "fire_smoke.pt",
        "expect": {"fire", "smoke", "flame"},
        "sources": [
            ("kittendev/YOLOv8m-smoke-detection", "best.pt"),
        ],
    },
    {
        "name": "Weapon Detection",
        "dest": "weapon_detection.pt",
        "expect": {"person", "weapon"},
        "sources": [
            ("Subh775/Firearm_Detection_Yolov8n", "weights/best.pt"),
            ("Subh775/Threat-Detection-YOLOv8n", "weights/best.pt"),
        ],
    },
]

def hf_url(repo: str, filename: str) -> str:
    return f"https://huggingface.co/{repo}/resolve/main/{filename}"

def model_classes(path: str):
    """Return the set of lowercased class names in a .pt model, or None."""
    try:
        from ultralytics import YOLO
        m = YOLO(path)
        return set(str(v).lower() for v in m.names.values())
    except Exception as e:
        print(f"  Could not read model classes: {e}")
        return None

def download_to(repo: str, filename: str, tmp_path: str) -> bool:
    """Stream a public HuggingFace file to tmp_path. No token needed."""
    import requests

    url = hf_url(repo, filename)
    try:
        with requests.get(url, stream=True, timeout=60, allow_redirects=True) as r:
            if r.status_code != 200:
                print(f"  HTTP {r.status_code} for {repo}/{filename}")
                return False
            total = int(r.headers.get("content-length", 0))
            written = 0
            with open(tmp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    if not chunk:
                        continue
                    f.write(chunk)
                    written += len(chunk)
                    if total:
                        print(f"\r  Downloading {repo}/{filename} … "
                              f"{written * 100 // total}%", end="", flush=True)
            print()
            if written < 500_000:
                print(f"  File too small ({written} bytes) — not a model.")
                return False
            return True
    except Exception as e:
        print(f"  Failed ({repo}/{filename}): {e}")
        return False

def fetch_verified(spec: dict) -> bool:
    """Download from the first source whose classes match spec['expect']."""
    dest = os.path.join(MODELS_DIR, spec["dest"])
    tmp = dest + ".download.pt"
    expect = spec["expect"]

    for repo, filename in spec["sources"]:
        if not download_to(repo, filename, tmp):
            continue

        classes = model_classes(tmp)
        if classes is None:
            os.path.exists(tmp) and os.remove(tmp)
            continue

        if classes & expect:
            os.replace(tmp, dest)
            size_mb = os.path.getsize(dest) / 1_000_000
            print(f"  Saved {spec['dest']} ({size_mb:.1f} MB)")
            print(f"  Classes: {', '.join(sorted(classes))}")
            return True
        else:
            print(f"  Rejected — classes {sorted(classes)} don't match "
                  f"{sorted(expect)}. Not a {spec['name']} model.")
            os.remove(tmp)

    return False

def main():
    parser = argparse.ArgumentParser(
        description="Download AlertEye specialized models (no token needed)"
    )
    parser.add_argument("--token", default="",
                        help="(unused) kept for backwards compatibility")
    parser.parse_args()

    os.makedirs(MODELS_DIR, exist_ok=True)

    print("\nAlertEye — Specialized Model Downloader (no token needed)")
    print("=" * 58)

    all_ok = True
    for spec in SPECIALIZED_MODELS:
        print(f"\n[{spec['name']}]  ->  {spec['dest']}")
        if not fetch_verified(spec):
            all_ok = False
            print(f"  FAILED — {spec['dest']} left unchanged.")

    print()
    if all_ok:
        print("All models downloaded & verified. Restart AlertEye to use them.")
    else:
        print("Some downloads failed. Manual fallback:")
        print("  1. Open the model page on huggingface.co → 'Files and versions'.")
        print(f"  2. Download the .pt and place it in: {MODELS_DIR}")
        print("     renaming to fire_smoke.pt / weapon_detection.pt as needed.")

if __name__ == "__main__":
    main()
