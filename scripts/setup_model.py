#!/usr/bin/env python3
"""
setup_model.py — Download Gemma 4 E2B INT4 model for Android on-device inference.

The model (~1.3 GB) cannot be bundled in the APK (assets limit).
This script downloads it and provides ADB push instructions to copy it
to the Android device's app files directory.

Usage:
  python scripts/setup_model.py [--output-dir <path>]

Requirements:
  pip install kagglehub
  Set KAGGLE_USERNAME and KAGGLE_KEY environment variables (from kaggle.com/account)
"""

import os
import sys
import argparse
import shutil
from pathlib import Path

SCRIPT_DIR   = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_OUT  = PROJECT_ROOT / "model_cache"

# Kaggle model handle for Gemma 4 E2B IT (the full-precision version).
# The LiteRT INT4 quantized .bin for MediaPipe is sourced from the same Kaggle page.
# Check https://www.kaggle.com/models/google/gemma for the exact path.
# Override at runtime: set GEMMA_MODEL_HANDLE env var to your specific handle.
MODEL_HANDLE = os.environ.get(
    "GEMMA_MODEL_HANDLE",
    "google/gemma-4/keras/gemma-4-2b-it/1"
)

APP_PACKAGE  = "com.gemma.triage"
DEVICE_PATH  = f"/data/data/{APP_PACKAGE}/files/gemma4e2b_int4.bin"
LOCAL_BIN    = "gemma4e2b_int4.bin"


def check_kagglehub():
    try:
        import kagglehub
        return kagglehub
    except ImportError:
        print("ERROR: kagglehub not installed.")
        print("  Run: pip install kagglehub")
        sys.exit(1)


def download_model(output_dir: Path) -> Path:
    kagglehub = check_kagglehub()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading Gemma 4 E2B INT4 from Kaggle...")
    print(f"  Handle: {MODEL_HANDLE}")
    print(f"  Output: {output_dir}")
    print(f"  Note: If this handle is wrong, set GEMMA_MODEL_HANDLE env var.")
    print(f"        Check: https://www.kaggle.com/models/google/gemma")
    print()

    try:
        # kagglehub downloads to a local cache; we copy to output_dir
        cached = kagglehub.model_download(MODEL_HANDLE)
        src = Path(cached)
        # Find the .bin file
        bin_files = list(src.rglob("*.bin"))
        if not bin_files:
            print(f"ERROR: No .bin file found in downloaded model at {src}")
            print(f"  Contents: {list(src.rglob('*'))}")
            sys.exit(1)

        dest = output_dir / LOCAL_BIN
        print(f"Copying {bin_files[0]} → {dest}")
        shutil.copy2(bin_files[0], dest)
        return dest

    except Exception as e:
        print(f"ERROR during download: {e}")
        print()
        print("Troubleshooting:")
        print("  1. If the MODEL_HANDLE is wrong, set GEMMA_MODEL_HANDLE env var:")
        print("       export GEMMA_MODEL_HANDLE=google/gemma-4/keras/gemma-4-2b-it/1")
        print("       Check: https://www.kaggle.com/models/google/gemma")
        print("  2. Ensure KAGGLE_USERNAME and KAGGLE_KEY are set:")
        print("       export KAGGLE_USERNAME=your_username")
        print("       export KAGGLE_KEY=your_api_key")
        print("  3. Accept the Gemma model license at https://www.kaggle.com/models/google/gemma")
        print("  4. Try: kagglehub model download " + MODEL_HANDLE)
        sys.exit(1)


def print_adb_instructions(model_path: Path):
    print()
    print("=" * 60)
    print("Model downloaded. Push to Android device with ADB:")
    print("=" * 60)
    print()
    print(f"  # 1. Connect device via USB (USB debugging enabled)")
    print(f"  adb push \"{model_path}\" {DEVICE_PATH}")
    print()
    print(f"  # 2. Verify:")
    print(f"  adb shell ls -lh /data/data/{APP_PACKAGE}/files/")
    print()
    print(f"  # 3. Install and run the app:")
    print(f"  cd android && ./gradlew installDebug")
    print()
    print("The app reads the model from context.filesDir/gemma4e2b_int4.bin")
    print("(set in TriageViewModel.loadModelAsync)")
    print()


def main():
    parser = argparse.ArgumentParser(description="Download Gemma 4 E2B INT4 for Android")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_OUT),
        help=f"Directory to save model (default: {DEFAULT_OUT})"
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    # Check for Kaggle credentials
    if not os.environ.get("KAGGLE_USERNAME") or not os.environ.get("KAGGLE_KEY"):
        print("WARNING: KAGGLE_USERNAME or KAGGLE_KEY not set.")
        print("  You may be prompted for credentials.")
        print()

    model_path = download_model(output_dir)
    print_adb_instructions(model_path)

    print(f"Done. Model at: {model_path}")


if __name__ == "__main__":
    main()
