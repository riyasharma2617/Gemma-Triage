#!/bin/bash
# Script to download the base Gemma 2B Instruct model from Hugging Face
# Requires `huggingface-cli` and valid HF token

set -e

MODEL_ID="google/gemma-2b-it"
TARGET_DIR="../model/gemma-2b-it"

echo "Downloading $MODEL_ID to $TARGET_DIR..."
huggingface-cli download $MODEL_ID --local-dir $TARGET_DIR --exclude "*.safetensors" # Exclude safetensors if using standard PyTorch weights, adjust as needed

echo "Download complete! Ready for conversion."
