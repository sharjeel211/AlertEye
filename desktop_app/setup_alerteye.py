"""
AlertEye - Setup & Installation Script
Run this once after cloning to install dependencies and download models.
Usage: python setup_alerteye.py
"""

import os
import sys
import subprocess
import platform

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable

def print_banner():
    print("\n" + "═" * 60)
    print("     ALERTEYE — Intelligent Surveillance System")
    print("     Setup & Installation Script v1.0")
    print("═" * 60 + "\n")

def check_python():
    """Check Python version."""
    v = sys.version_info
    version_str = f"{v.major}.{v.minor}.{v.micro}"

    if v.major < 3 or (v.major == 3 and v.minor < 9):
        print(f"✗ Python 3.9+ required. Current: {version_str}")
        sys.exit(1)

    print(f"✓ Python {version_str}")
    if v.major == 3 and v.minor >= 13:
        print("  ℹ Python 3.13+ detected — using PySide6 (full support ✓)")

def check_cuda():
    """Check CUDA availability."""
    try:
        import torch
        if torch.cuda.is_available():
            device = torch.cuda.get_device_name(0)
            print(f"✓ CUDA available: {device}")
            return True
        else:
            print("  ℹ CUDA not available — will use CPU")
            return False
    except ImportError:
        print("  ℹ PyTorch not installed yet")
        return False

def install_dependencies():
    """Install Python packages — installs critical ones first, skips optional failures."""
    print("\n📦 Installing dependencies...")

    critical = [
        "PySide6>=6.6.0",
        "opencv-python>=4.8.0",
        "numpy>=1.24.0",
        "Pillow>=10.0.0",
        "requests>=2.31.0",
        "psutil>=5.9.0",
        "pyyaml>=6.0",
        "colorlog>=6.7.0",
        "tqdm>=4.65.0",
    ]

    heavy = [
        "torch>=2.0.0",
        "torchvision>=0.15.0",
        "ultralytics>=8.0.0",
    ]

    optional = [
        "scipy>=1.11.0",
        "pandas>=2.0.0",
        "GPUtil>=1.4.0",
    ]

    def pip_install(packages, label):
        result = subprocess.run(
            [PYTHON, "-m", "pip", "install", "--upgrade"] + packages,
            cwd=PROJECT_ROOT,
            capture_output=False
        )
        if result.returncode != 0:
            print(f"  ⚠  Some {label} packages failed — continuing...")
            return False
        return True

    print("\n  → Installing core UI & vision packages...")
    pip_install(critical, "core")

    print("\n  → Installing AI/ML packages (this may take a few minutes)...")
    pip_install(heavy, "AI/ML")

    print("\n  → Installing optional packages...")
    for pkg in optional:
        r = subprocess.run(
            [PYTHON, "-m", "pip", "install", "--upgrade", pkg],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True
        )
        status = "✓" if r.returncode == 0 else "⚠ (skipped)"
        print(f"    {status} {pkg}")

    print("\n✓ Dependencies installation complete.")
    return True

def create_directories():
    """Create required directories."""
    print("\n📁 Creating directories...")
    dirs = [
        "models", "logs", "screenshots", "recordings",
        "assets/sounds", "assets/icons", "config"
    ]
    for d in dirs:
        path = os.path.join(PROJECT_ROOT, d)
        os.makedirs(path, exist_ok=True)
        print(f"  ✓ {d}")

def generate_alert_sound():
    """Generate a default alert sound file."""
    try:
        import numpy as np
        sound_path = os.path.join(PROJECT_ROOT, "assets", "sounds", "alert.wav")
        if os.path.exists(sound_path):
            return

        print("\n🔊 Generating alert sound...")
        sample_rate = 44100
        duration = 0.8
        t = np.linspace(0, duration, int(sample_rate * duration))

        freq1, freq2 = 880, 660
        wave = np.sin(2 * np.pi * freq1 * t) * 0.5
        wave[len(wave) // 2:] = np.sin(2 * np.pi * freq2 * t[:len(t) // 2]) * 0.5

        import struct
        wave_int = (wave * 32767).astype(np.int16)
        with open(sound_path, "wb") as f:
            data_size = len(wave_int) * 2
            f.write(b"RIFF")
            f.write(struct.pack("<I", data_size + 36))
            f.write(b"WAVE")
            f.write(b"fmt ")
            f.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate,
                               sample_rate * 2, 2, 16))
            f.write(b"data")
            f.write(struct.pack("<I", data_size))
            f.write(wave_int.tobytes())
        print(f"  ✓ Alert sound generated: {sound_path}")
    except Exception as e:
        print(f"  ℹ Could not generate sound: {e}")

def download_models():
    """Download required models."""
    print("\n🤖 Checking AI models...")
    sys.path.insert(0, PROJECT_ROOT)
    try:
        from utils.model_downloader import download_all_models, model_exists, MODEL_REGISTRY

        missing = [
            name for name, info in MODEL_REGISTRY.items()
            if not model_exists(info["filename"])
        ]

        if not missing:
            print("  ✓ All models already present.")
            return True

        print(f"  ℹ {len(missing)} models need to be downloaded.")
        choice = input("\n  Download now? [Y/n]: ").strip().lower()
        if choice in ("", "y", "yes"):
            def progress(name, cur, total, success):
                s = "✓" if success else "✗"
                print(f"    [{s}] ({cur}/{total}) {name}")
            results = download_all_models(progress_cb=progress)
            ok = sum(1 for v in results.values() if v)
            print(f"\n  Downloaded {ok}/{len(results)} models.")
        else:
            print("  ℹ Skipped model download. Models will be downloaded on first use.")
    except Exception as e:
        print(f"  ✗ Model download failed: {e}")
    return True

def create_launch_scripts():
    """Create OS-specific launch scripts."""
    print("\n🚀 Creating launch scripts...")

    launcher_py = os.path.join(PROJECT_ROOT, "run.py")
    with open(launcher_py, "w") as f:
        f.write('#!/usr/bin/env python3\n"""Quick launcher for AlertEye."""\n')
        f.write('import os, sys\n')
        f.write('sys.path.insert(0, os.path.dirname(__file__))\n')
        f.write('from main import main\nmain()\n')
    print("  ✓ run.py")

    if platform.system() == "Windows":
        bat_path = os.path.join(PROJECT_ROOT, "alerteye.bat")
        with open(bat_path, "w") as f:
            f.write(f'@echo off\n"{PYTHON}" "{launcher_py}"\npause\n')
        print(f"  ✓ alerteye.bat")
    else:
        sh_path = os.path.join(PROJECT_ROOT, "alerteye.sh")
        with open(sh_path, "w") as f:
            f.write(f'#!/bin/bash\ncd "{PROJECT_ROOT}"\n"{PYTHON}" run.py\n')
        os.chmod(sh_path, 0o755)
        print(f"  ✓ alerteye.sh")

def main():
    print_banner()
    check_python()
    create_directories()

    install_choice = input("\n📦 Install/update Python dependencies? [Y/n]: ").strip().lower()
    if install_choice in ("", "y", "yes"):
        install_dependencies()

    check_cuda()
    generate_alert_sound()
    download_models()
    create_launch_scripts()

    print("\n" + "═" * 60)
    print("  ✓ Setup complete!")
    print("\n  To launch AlertEye:")
    print(f"    {PYTHON} main.py")
    if platform.system() == "Windows":
        print("    or double-click: alerteye.bat")
    else:
        print("    or run: ./alerteye.sh")
    print("═" * 60 + "\n")

if __name__ == "__main__":
    main()
