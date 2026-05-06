# Feature: Phase 5 — Python Demo
**Phase:** 5 | **Status:** complete

## What It Does
CLI demo that simulates the Android triage pipeline via the Gemini API. Demonstrates the full flow: patient description in → START triage assessment → color-coded result + SMS payload + follow-up conversation loop. Also includes a model setup script for downloading the on-device model for Android.

## Key Files
- `python_demo/triage_demo.py` — Interactive CLI (and batch CSV mode) using google-generativeai SDK; temperature 0.1 for initial triage, 0.3 for follow-up; reads system prompt from android assets
- `python_demo/requirements.txt` — Single dependency: google-generativeai>=0.8.0
- `scripts/setup_model.py` — Downloads Gemma 4 E2B INT4 from Kaggle via kagglehub, outputs ADB push instructions for Android device deployment

## How to Test
```bash
# Interactive mode
pip install -r python_demo/requirements.txt
export GEMINI_API_KEY=your_key_here
python python_demo/triage_demo.py

# Batch mode (CSV with one patient description per row)
python python_demo/triage_demo.py --batch --file patients.csv

# Model setup (requires Kaggle credentials)
export KAGGLE_USERNAME=your_username
export KAGGLE_KEY=your_api_key
python scripts/setup_model.py
```

## Known Limitations
- Uses Gemini API (cloud), not on-device Gemma — this is intentional for demo purposes, the Android app uses on-device inference
- Model handle in setup_model.py (`GEMMA_MODEL_HANDLE` env var) defaults to `google/gemma-4/keras/gemma-4-2b-it/1` — verify exact Kaggle path for INT4 LiteRT binary at https://www.kaggle.com/models/google/gemma
- kagglehub is NOT in requirements.txt (only needed for model download); install separately: `pip install kagglehub`
