#!/usr/bin/env python3
"""Download required model files for the Interview Analytics pipeline.

Run this script once with internet access:
    python scripts/download_models.py

Models downloaded:
    - WeSpeaker ResNet34 ONNX (~26 MB) → models/wespeaker/voxceleb_resnet34_LM.onnx
    - Silero VAD and faster-whisper models are auto-cached by their libraries.
"""
import urllib.request
from pathlib import Path
import os
import sys

# Models configuration
WESPEAKER_URL = "https://huggingface.co/onnx-community/wespeaker-voxceleb-resnet34-LM/resolve/main/onnx/model.onnx"
WESPEAKER_DEST = Path("models/wespeaker/voxceleb_resnet34_LM.onnx")

def download_wespeaker():
    """Download WeSpeaker ResNet34 ONNX model from HuggingFace."""
    if WESPEAKER_DEST.exists():
        size_mb = WESPEAKER_DEST.stat().st_size / (1024 * 1024)
        print(f"[OK] WeSpeaker model already exists: {WESPEAKER_DEST} ({size_mb:.1f} MB)")
        return
    
    WESPEAKER_DEST.parent.mkdir(parents=True, exist_ok=True)
    print(f"[DOWNLOAD] Downloading WeSpeaker ResNet34 ONNX model...")
    print(f"  Source: {WESPEAKER_URL}")
    print(f"  Destination: {WESPEAKER_DEST}")
    
    try:
        urllib.request.urlretrieve(WESPEAKER_URL, str(WESPEAKER_DEST))
        size_mb = WESPEAKER_DEST.stat().st_size / (1024 * 1024)
        print(f"[OK] Download complete: {size_mb:.1f} MB")
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        if WESPEAKER_DEST.exists():
            WESPEAKER_DEST.unlink()
        raise

def main():
    print("="*50)
    print("Interview Analytics - Model Downloader")
    print("="*50)
    
    download_wespeaker()
    
    print("\n" + "="*50)
    print("All models ready.")
    print("="*50)

if __name__ == "__main__":
    main()
