# Gemma Triage

**Offline AI-powered emergency triage assistant for first responders — built on Google Gemma 4, running fully on-device.**

Built for the **[Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good)** — Global Resilience Track + LiteRT Special Prize.

---

## The Problem

Every second matters in a mass-casualty incident (MCI). A bus crash, building collapse, or natural disaster can produce dozens of critical patients simultaneously, overwhelming the few first responders on scene. Their job is to perform **START triage** — a rapid 60-second assessment per patient that determines who gets care first and who must wait.

The problem is that first responders are working under:

- **Extreme cognitive load** — noise, chaos, injured colleagues, time pressure
- **No internet** — cell towers collapse under disaster load or are physically destroyed
- **No power grid** — mobile command centers lose connectivity
- **Both hands occupied** — holding airways, applying pressure, moving patients

Current triage tools are paper tags and radio calls. An AI that could listen, assess, and speak the verdict would save lives — but only if it works **with zero connectivity, on a phone already in the responder's pocket.**

That is what Gemma Triage solves.

---

## What It Does

A first responder holds their phone near a patient and speaks:

> *"Adult male, struck by vehicle. Breathing 34 per minute, no radial pulse, cap refill four seconds."*

Within seconds, the app responds aloud:

> *"RED. Immediate life threat. Control bleeding, airway positioning, flag for immediate transport."*

The verdict is also:

- Color-coded on screen (RED / YELLOW / GREEN / BLACK)
- Logged to an encrypted on-device audit trail
- Compressed into a 160-character SMS payload ready to dispatch when signal returns

The responder can then ask follow-up questions in conversation:

> *"What's the bleeding control priority here?"*
> *"Should I move him or wait for the stretcher?"*

Everything — speech recognition, AI reasoning, text-to-speech, database — runs **entirely offline on the Android device.**

---

## Why We Built This

We both came to this hackathon from different angles but with the same instinct: **the communities most at risk from disasters are the ones least likely to have reliable infrastructure.** Rural areas, conflict zones, earthquake regions — these are exactly where triage decisions matter most and where LTE is the first thing to fail.

We chose the **Global Resilience Track** because it forced us to build something real. No server to fall back on. No API to call. If it doesn't work on the phone, it doesn't work.

The **LiteRT Special Prize** aligned perfectly — the entire project is designed around on-device inference. The model was fine-tuned specifically for this task, quantized to INT4, converted to the MediaPipe `.task` format, and optimized to run on commodity Android hardware without NPU assistance.

We wanted to prove that a fine-tuned, domain-specific small language model can match the accuracy of a much larger general model for a well-defined, high-stakes task — and do it in your pocket, offline, in under 5 seconds.

---

## How We Built It

The project is organized as a sequential pipeline. Each stage has a clear input and output.

### Stage 1 — Dataset Creation (`01_data/`)

We built **496 curated training examples** and **100 held-out test cases**, covering all four START triage outcomes (RED, YELLOW, GREEN, BLACK) across a range of MCI scenarios: vehicle collisions, explosions, building collapses, crush injuries, burns, and drowning.

Each example is a realistic spoken patient description paired with a structured JSON output containing:

- Triage code and confidence score
- Clinical reasoning citing specific START criteria
- Immediate action steps
- Monitoring checklist and warning signs
- A compressed SMS payload

We ran a **data leakage check** (`scripts/check_leakage.py`) using ROUGE-L similarity to verify zero overlap between training and test sets before any model work began. The test set was locked on Day 1 and never touched again.

Class distribution was intentionally imbalanced to match real MCI statistics: RED cases are most common and most consequential — the model must get these right.

### Stage 2 — Base Model Evaluation (`02_evaluate_base/`)

Before fine-tuning, we evaluated `google/gemma-4-E2B-it` on our test set with our system prompt. This step exists to answer one question: **does fine-tuning actually help?**

We measured:

- Triage code accuracy per class
- JSON compliance rate
- Parse error types (`MALFORMED_JSON`, `MISSING_KEY`, `INVALID_CODE`)
- F1 on RED and BLACK (the safety-critical classes)

This baseline determines whether fine-tuning is worth doing and provides the comparison target for Stage 4.

### Stage 3 — QLoRA Fine-Tuning on Kaggle (`03_finetune/`)

We fine-tuned using **QLoRA** (Quantized Low-Rank Adaptation) on a Kaggle P100 GPU (free tier, 16 GB VRAM):

- **Base model:** `google/gemma-4-E2B-it` loaded in 4-bit via Unsloth
- **LoRA rank:** 16, alpha 32, targeting all attention and MLP projections
- **Training:** 5 epochs, cosine LR schedule, early stopping on validation loss
- **Effective batch size:** 16 (batch 2 × gradient accumulation 8)
- **Validation split:** 10% held out during training to detect overfitting

The training data was formatted in Gemma 4's native `<start_of_turn>` / `<end_of_turn>` chat template. We pre-seeded model turns with `{` to enforce JSON output from the first token.

After training, LoRA adapters were merged back into the base model weights and saved.

Configuration is centralized in `pipeline_config.json` — no hyperparameters are hardcoded in notebooks.

### Stage 4 — Fine-Tuned Evaluation (`04_evaluate_finetuned/`)

We ran the identical evaluation suite from Stage 2 on the fine-tuned model and compared:

- Delta F1 on RED and BLACK (success threshold: F1 ≥ 0.92 for both)
- Delta JSON compliance rate (target: zero parse errors on test set)
- Confidence calibration

This stage gates conversion — we only proceed to Stage 5 if the fine-tuned model improves on the safety-critical metrics.

### Stage 5 — LiteRT Conversion (`05_convert/`)

The fine-tuned HuggingFace model is converted to MediaPipe's `.task` format for on-device inference:

1. `to_tflite.py` — converts PyTorch weights to LiteRT flatbuffer via `ai-edge-torch`, applying INT4 quantization calibrated on representative triage prompts
2. `bundle_task.py` — bundles quantized weights + SentencePiece tokenizer into a single `.task` file

INT4 quantization reduces the ~4 GB merged model to ~1 GB on disk, making it practical to push to a device over ADB and load into memory alongside the Android system.

### Stage 6 — Android App (`android/`)

Built in Kotlin with the MediaPipe LLM Inference API, the app implements the full pipeline:

| Component | Technology |
| --- | --- |
| On-device inference | MediaPipe `tasks-genai` + LiteRT |
| Speech recognition | Android `SpeechRecognizer` (offline) |
| Text-to-speech | Android `TextToSpeech` |
| Noise suppression | Android `NoiseSuppressor` + VAD |
| Audit trail | Room database |
| SMS dispatch | Android `SmsManager` + queue |
| UI | Material 3, ViewPager2 |
| Architecture | MVVM + sealed state machine |

The inference engine runs on a **dedicated single-threaded executor** to prevent re-entrant calls to the LiteRT runtime. Greedy decoding (`topK=1`, `temperature=0.1`) is used for triage to ensure deterministic outputs — the same symptoms always produce the same triage code.

---

## Project Structure

```text
gemma-triage/
├── 01_data/                    ← Dataset creation and validation
│   ├── curated/                ← 496 training examples (JSONL)
│   ├── test_set.jsonl          ← 100 held-out test cases (locked Day 1)
│   ├── build_dataset.py        ← Synthetic example generation
│   └── leakage_report.json     ← ROUGE-L leakage check results
│
├── 02_evaluate_base/           ← Base model evaluation (pre fine-tune)
│   └── eval_base_model.py
│
├── 03_finetune/                ← QLoRA fine-tuning scripts
│   ├── train.py                ← Unsloth + SFTTrainer
│   ├── merge_lora.py           ← Merge adapters → full model
│   └── config.yaml             ← Hyperparameters (also in pipeline_config.json)
│
├── 04_evaluate_finetuned/      ← Post fine-tune evaluation and comparison
│   └── eval_finetuned.py
│
├── 05_convert/                 ← LiteRT conversion pipeline
│   ├── to_tflite.py            ← ai-edge-torch → INT4 TFLite
│   └── bundle_task.py          ← TFLite + tokenizer → MediaPipe .task
│
├── 06_inference/               ← Local inference test harness
│   └── infer.py
│
├── android/                    ← Android application
│   └── app/src/main/java/com/gemma/triage/
│       ├── inference/          ← GemmaInferenceEngine, PromptBuilder
│       ├── audio/              ← STT, TTS, VAD
│       ├── output/             ← SMS formatter, queue manager
│       ├── storage/            ← Room database
│       └── viewmodel/          ← TriageViewModel, TriageUiState
│
├── scripts/
│   ├── setup_model.py          ← Download model from Kaggle + ADB push
│   ├── check_leakage.py        ← Dataset leakage validation
│   └── eval_utils.py           ← Shared evaluation helpers
│
├── tests/                      ← Python unit tests for pipeline scripts
├── pipeline_config.json        ← Central config for all pipeline stages
└── README.md
```

---

## Setup and Running

### Prerequisites

- Android device with Android 8.0+ (API 26), 6 GB RAM recommended
- ADB installed and USB debugging enabled on device
- Python 3.10+
- Kaggle account with Gemma license accepted

### Step 1 — Accept the model license

- [kaggle.com/models/google/gemma](https://www.kaggle.com/models/google/gemma) → accept Gemma 4 license
- [huggingface.co/google/gemma-4-E2B-it](https://huggingface.co/google/gemma-4-E2B-it) → accept HuggingFace license

### Step 2 — Download the model

```bash
pip install kagglehub
export KAGGLE_USERNAME=your_username
export KAGGLE_KEY=your_api_key

python scripts/setup_model.py
# Tries Gemma 4 INT4 first, falls back through alternatives automatically
# Prints the exact ADB command to use
```

### Step 3 — Push model to device

```bash
# The exact command is printed by setup_model.py — copy it
adb push "model_cache/gemma4e2b_int4.task" /data/data/com.gemma.triage/files/gemma4e2b_int4.task

# Verify
adb shell ls -lh /data/data/com.gemma.triage/files/
```

### Step 4 — Build and install

```bash
cd android
./gradlew installDebug
```

The app auto-detects whichever model file is present in `context.filesDir`.

### Running the Fine-Tuning Pipeline (optional)

If you want to reproduce the fine-tuning from scratch:

1. Upload `01_data/curated/training_dataset.jsonl` and `01_data/test_set.jsonl` to a Kaggle dataset named `gemma-triage-data`
2. Run `scripts/check_leakage.py` locally to verify the test set is clean
3. Run notebooks in order: `02_evaluate_base` → `03_finetune` → `04_evaluate_finetuned` → `05_convert`
4. All hyperparameters are in `pipeline_config.json`

### Running Python Tests

```bash
pip install pytest rouge-score
pytest tests/
```

---

## Technical Highlights

**Fully offline.** The app has no `INTERNET` permission in the manifest. It cannot make network requests — not even accidentally. All data stays on the device.

**Deterministic triage.** Greedy decoding (`topK=1`) means the same symptoms always produce the same triage code. This is a deliberate safety choice: medical decisions must not vary by random seed.

**Fault-tolerant JSON parsing.** The model output parser handles preamble text before the JSON object, truncated outputs, and missing fields — falling back to `UNKNOWN` rather than crashing, so the responder always gets a response even if the model output is malformed.

**Single-threaded inference executor.** The LiteRT runtime is not thread-safe. All calls to `LlmInference` are serialized through a dedicated named thread (`gemma-inference`), preventing concurrent call crashes.

**Graceful model resolution.** The app tries multiple model filenames in priority order, so it works with pre-converted Kaggle models, custom-converted models, and development fallbacks without code changes.

---

## Permissions

| Permission | Why |
| --- | --- |
| `RECORD_AUDIO` | Voice input from first responder |
| `SEND_SMS` | Dispatch compressed triage payload when signal returns |
| `READ_PHONE_STATE` | SMS routing and SIM selection |
| `ACCESS_FINE_LOCATION` | Optional: attach GPS coordinates to SMS dispatch |

No `INTERNET` permission. No data leaves the device during triage.

---

## Contributors

| Name | Expertise | Contributions |
| --- | --- | --- |
| **Riya Sharma** | AI / ML Engineer | Dataset design, QLoRA fine-tuning, model evaluation, LiteRT conversion pipeline |
| **Priyanshu Arya** | AI / ML Expert + Android Engineer | Data collection, fine-tuning pipeline, model integration, Android app (Vibe Coded) — speech pipeline, UI, SMS system, inference engine |

> **Vibe Coding:** The entire Android application was designed and built by Priyanshu using AI-assisted development — rapidly prototyping, iterating, and shipping production-grade Kotlin code with the help of LLM tooling throughout the build process.

---

## Hackathon

**Competition:** [Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good) by Google & Kaggle

**Tracks:**

- Global Resilience Track
- LiteRT Special Prize

**Model:** Google Gemma 4 E2B-IT, fine-tuned on 496 curated triage examples, quantized to INT4, deployed via MediaPipe LiteRT

---

## License

This project is submitted as part of the Gemma 4 Good Hackathon. The fine-tuned model weights and training data are subject to the [Gemma Terms of Use](https://ai.google.dev/gemma/terms). The application code is MIT licensed.
