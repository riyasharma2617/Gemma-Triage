"""
Notebook 4 continuation — validate exported model F1 and run privacy check.
Run after to_tflite.py cells in the same Kaggle session.

Variables expected from to_tflite.py session state:
  export_report, cfg, out, tokenizer, sys (already imported)
"""

# === CELL 5: F1 validation on exported model (Path A only — mediapipe) ===
# For GGUF/TFLite paths, F1 validation requires the corresponding inference engine.
# Skip this cell if export_report["path_succeeded"] != "mediapipe"

if export_report.get("path_succeeded") == "mediapipe":
    from eval_utils import build_prompt, parse_triage_code, compute_metrics
    from mediapipe.tasks.python.genai import inference as mp_llm

    test_cases = json.loads(open(cfg["test_set_path"]).read())["cases"]
    train_cases = [json.loads(l) for l in open(cfg["training_data_path"])]
    first_msg = train_cases[0]["messages"][0]
    system_prompt = first_msg["content"] if first_msg["role"] == "system" \
        else first_msg["content"].split("\n\nNow, respond")[0]

    def eval_task_file(task_path):
        llm = mp_llm.LlmInference.create_from_options(
            mp_llm.LlmInferenceOptions(model_path=str(task_path), max_tokens=256, top_k=1)
        )
        preds, labels, sources = [], [], []
        for case in test_cases:
            prompt = build_prompt(tokenizer, system_prompt, case["description"])
            raw    = llm.generate_response(prompt)
            code, _ = parse_triage_code(raw)
            preds.append(code)
            labels.append(case["expected_code"])
            sources.append(case.get("source", "generated"))
        return compute_metrics(preds, labels, sources)

    print("Evaluating INT4 model...")
    int4_metrics = eval_task_file(out / "gemma_triage_int4.task")
    print("Evaluating INT8 model...")
    int8_metrics = eval_task_file(out / "gemma_triage_int8.task")

    print(f"\nINT4: RED F1={int4_metrics['per_class']['RED']['f1']:.3f}  "
          f"BLACK F1={int4_metrics['per_class']['BLACK']['f1']:.3f}  "
          f"macro={int4_metrics['macro_f1']:.3f}")
    print(f"INT8: RED F1={int8_metrics['per_class']['RED']['f1']:.3f}  "
          f"BLACK F1={int8_metrics['per_class']['BLACK']['f1']:.3f}  "
          f"macro={int8_metrics['macro_f1']:.3f}")

    int4_red_drop   = int8_metrics["per_class"]["RED"]["f1"]   - int4_metrics["per_class"]["RED"]["f1"]
    int4_black_drop = int8_metrics["per_class"]["BLACK"]["f1"] - int4_metrics["per_class"]["BLACK"]["f1"]
    export_report["int4_f1_drop_red"]   = round(float(int4_red_drop),   4)
    export_report["int4_f1_drop_black"] = round(float(int4_black_drop), 4)

    threshold = cfg["f1_drop_threshold_critical"]
    if int4_red_drop <= threshold and int4_black_drop <= threshold:
        chosen = out / "gemma_triage_int4.task"
        export_report["quantization_used"] = "int4"
        print(f"+ INT4 drop within threshold ({threshold}) -> shipping INT4")
    else:
        chosen = out / "gemma_triage_int8.task"
        export_report["quantization_used"] = "int8"
        print(f"  INT4 drop exceeds threshold -> shipping INT8 (accuracy > size)")

    chosen_size = chosen.stat().st_size / 1e6
    export_report["output_file"] = chosen.name
    export_report["file_size_mb"] = round(chosen_size, 1)
    print(f"  Final model: {chosen.name} ({chosen_size:.0f} MB)")


# === CELL 6: Privacy check (verbatim + 5-gram) ===
from collections import Counter


def ngram_overlap(text_a: str, text_b: str, n: int = 5) -> float:
    """Fraction of n-grams in text_a that appear in text_b."""
    words_a = text_a.lower().split()
    words_b = text_b.lower().split()
    if len(words_a) < n or len(words_b) < n:
        return 0.0
    grams_a = Counter(zip(*[words_a[i:] for i in range(n)]))
    grams_b = set(zip(*[words_b[i:] for i in range(n)]))
    overlap = sum(v for g, v in grams_a.items() if g in grams_b)
    return overlap / sum(grams_a.values())


privacy_failed = False
if export_report.get("path_succeeded") == "mediapipe":
    train_cases = [json.loads(l) for l in open(cfg["training_data_path"])]
    # Limit to first 20 training cases for speed (representative sample)
    for case in train_cases[:20]:
        msgs = case["messages"]
        description = msgs[1]["content"] if msgs[0]["role"] == "system" else msgs[0]["content"]
        ref_response = msgs[-1]["content"]

        prompt   = build_prompt(tokenizer, system_prompt, description)
        response = llm.generate_response(prompt)

        # 1. Verbatim check
        if ref_response in response:
            print(f"x Privacy FAIL (verbatim): case {case['metadata']['id']}")
            privacy_failed = True
            break

        # 2. 5-gram overlap check
        overlap = ngram_overlap(response, ref_response, n=5)
        if overlap >= cfg["privacy_ngram_overlap_limit"]:
            print(f"x Privacy FAIL (5-gram {overlap:.2f} >= "
                  f"{cfg['privacy_ngram_overlap_limit']}): case {case['metadata']['id']}")
            privacy_failed = True
            break

    if not privacy_failed:
        print("+ Privacy check passed (verbatim + 5-gram on 20 training cases)")

export_report["privacy_check_passed"] = not privacy_failed


# === CELL 7: Write final export report ===
(out / "export_report.json").write_text(json.dumps(export_report, indent=2))

print("\n=== Export Report ===")
print(json.dumps(export_report, indent=2))

if privacy_failed:
    raise RuntimeError(
        "Privacy check failed — model may be memorising training responses. "
        "Do NOT deploy. Reduce epochs or increase training set size."
    )

print(f"\n+ Export complete.")
print(f"  Output: {export_report['output_file']} ({export_report['file_size_mb']} MB)")
print(f"  Path:   {export_report['path_succeeded']}")
print(f"  Quant:  {export_report['quantization_used']}")
print(f"\n-> Drop {export_report['output_file']} into your Android app/src/main/assets/")
print("  See the spec (docs/superpowers/specs/2026-05-11-kaggle-pipeline-design.md) "
      "for Android Kotlin integration code.")
