"""
Notebook 4 — Export Fine-tuned Model for Android
Kaggle inputs required:
  - gemma-triage-data  (pipeline_config.json)
  - gemma-triage-outputs  (merged_model/)
  - gemma-triage-finetuned-eval  (pipeline_continue.json)
Output: gemma_triage.task / .gguf / .tflite
"""

# === CELL 1: Setup + gate check ===
import sys, json, pathlib, datetime
sys.path.append("/kaggle/input/gemma-triage-data")

cfg = json.loads(
    pathlib.Path("/kaggle/input/gemma-triage-data/pipeline_config.json").read_text()
)

gate = json.loads(
    open("/kaggle/input/gemma-triage-finetuned-eval/pipeline_continue.json").read()
)
assert gate["export_allowed"], (
    "Export blocked: NB3 detected a RED/BLACK F1 regression. "
    "Investigate training before proceeding."
)
print("+ Pipeline gate passed — export allowed")

merged_path = cfg["merged_model_path"]
out = pathlib.Path("/kaggle/working")
export_report = {
    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    "path_attempted": None,
    "path_succeeded": None,
    "output_file": None,
    "file_size_mb": None,
    "int4_f1_drop_red": None,
    "int4_f1_drop_black": None,
    "quantization_used": None,
    "privacy_check_passed": None,
}


# === CELL 2: Path A smoke test (tiny dummy model — avoids loading 4 GB for probe) ===
# !pip install ai_edge_torch>=0.3.0 -q

from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer
import tempfile, os

export_report["path_attempted"] = "mediapipe"
tokenizer = AutoTokenizer.from_pretrained(merged_path)
tokenizer.model_max_length = cfg["max_seq_length"]

config = AutoConfig.from_pretrained(merged_path)
config.num_hidden_layers = 2   # minimal — just verifies the conversion API
dummy_model = AutoModelForCausalLM.from_config(config)

path_a_viable = False
with tempfile.TemporaryDirectory() as tmp:
    dummy_model.save_pretrained(tmp)
    tokenizer.save_pretrained(tmp)
    try:
        import ai_edge_torch
        from ai_edge_torch.generative.quantize import QuantConfig
        from mediapipe.tasks.python.genai import inference as mp_llm

        ai_edge_torch.generative.convert(
            model_path=tmp,
            output_path=os.path.join(tmp, "smoke.task"),
            tokenizer=tokenizer,
            quant_config=QuantConfig(num_bits=8),
        )
        mp_llm.LlmInference.create_from_options(
            mp_llm.LlmInferenceOptions(model_path=os.path.join(tmp, "smoke.task"))
        )
        path_a_viable = True
        print("+ Path A smoke test PASSED -> proceeding with MediaPipe conversion")
    except Exception as e:
        print(f"x Path A smoke test FAILED: {e}")
        print("  -> Falling back to Path B (GGUF)")

del dummy_model  # free memory before loading real model


# === CELL 3A: Path A — full MediaPipe conversion (if smoke test passed) ===
if path_a_viable:
    import torch
    from transformers import AutoModelForCausalLM as AMFC

    real_model = AMFC.from_pretrained(
        merged_path, torch_dtype=torch.float16, device_map="auto"
    )

    print("Converting INT4...")
    ai_edge_torch.generative.convert(
        model_path=merged_path,
        output_path=str(out / "gemma_triage_int4.task"),
        tokenizer=tokenizer,
        quant_config=QuantConfig(num_bits=4),
    )
    print("Converting INT8...")
    ai_edge_torch.generative.convert(
        model_path=merged_path,
        output_path=str(out / "gemma_triage_int8.task"),
        tokenizer=tokenizer,
        quant_config=QuantConfig(num_bits=8),
    )

    int4_size = (out / "gemma_triage_int4.task").stat().st_size / 1e6
    int8_size = (out / "gemma_triage_int8.task").stat().st_size / 1e6
    print(f"  INT4: {int4_size:.0f} MB | INT8: {int8_size:.0f} MB")

    export_report["path_succeeded"] = "mediapipe"
    print("+ Path A complete. Run CELL 5 (F1 validation) before choosing INT4 vs INT8.")


# === CELL 3B: Path B — GGUF via llama.cpp (if Path A failed) ===
if not path_a_viable:
    export_report["path_attempted"] = "gguf"
    path_b_viable = False
    try:
        import requests
        src = requests.get(
            "https://raw.githubusercontent.com/ggerganov/llama.cpp/master/convert_hf_to_gguf.py",
            timeout=10,
        ).text
        if "Gemma4" in src or "gemma4" in src.lower():
            path_b_viable = True
            print("+ llama.cpp supports Gemma 4 -> proceeding with GGUF conversion")
        else:
            print("x llama.cpp does NOT yet support Gemma 4 -> falling back to Path C (ONNX->TFLite)")
    except Exception as e:
        print(f"x Could not check llama.cpp support: {e} -> falling back to Path C")

    if path_b_viable:
        import subprocess
        result = subprocess.run([
            "python", "convert_hf_to_gguf.py", merged_path,
            "--outfile", str(out / "gemma_triage_q4km.gguf"),
            "--outtype", "q4_K_M",
        ], capture_output=True, text=True)
        if result.returncode == 0:
            size = (out / "gemma_triage_q4km.gguf").stat().st_size / 1e6
            print(f"+ GGUF conversion complete | {size:.0f} MB")
            export_report["path_succeeded"] = "gguf"
            export_report["output_file"] = "gemma_triage_q4km.gguf"
        else:
            print(f"x GGUF conversion failed: {result.stderr}")
            path_b_viable = False

    if not path_b_viable:
        # === CELL 3C: Path C — ONNX -> TFLite ===
        export_report["path_attempted"] = "tflite"
        import subprocess

        print("Exporting to ONNX...")
        subprocess.run([
            "optimum-cli", "export", "onnx",
            "--model", merged_path,
            "--task", "text-generation",
            str(out / "gemma_onnx"),
        ], check=True)

        print("Converting ONNX -> TFLite (INT4)...")
        subprocess.run([
            "onnx2tf",
            "-i", str(out / "gemma_onnx" / "model.onnx"),
            "-o", str(out / "gemma_tflite"),
            "--quant_type", "int4",
        ], check=True)

        # Path C smoke test — onnx2tf can silently produce broken models
        import tensorflow as tf
        tflite_path = str(out / "gemma_tflite" / "model.tflite")
        interpreter = tf.lite.Interpreter(model_path=tflite_path)
        interpreter.allocate_tensors()
        input_detail = interpreter.get_input_details()[0]
        import numpy as np
        dummy_input = np.zeros(input_detail["shape"], dtype=input_detail["dtype"])
        interpreter.set_tensor(input_detail["index"], dummy_input)
        try:
            interpreter.invoke()
            print("+ Path C TFLite smoke test PASSED")
            export_report["path_succeeded"] = "tflite"
            export_report["output_file"] = "gemma_tflite/model.tflite"
        except Exception as e:
            raise RuntimeError(
                f"Path C TFLite smoke test FAILED: {e}\n"
                "No viable export path available. Check ai_edge_torch and llama.cpp compatibility."
            )


# === CELL 4: Report export status ===
print(f"\nExport path succeeded: {export_report['path_succeeded']}")
if export_report["path_succeeded"] is None:
    raise RuntimeError("All three export paths failed. See errors above.")
