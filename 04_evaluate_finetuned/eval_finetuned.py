"""
Notebook 3 — Fine-tuned Model Evaluation + Comparison
Kaggle inputs required:
  - gemma-triage-data  (dataset)
  - gemma-triage-outputs  (merged_model/)
  - gemma-triage-base-eval  (base_eval_results.json)
Output dataset: gemma-triage-finetuned-eval
  - finetuned_eval_results.json
  - finetuned_eval_errors.json
  - pipeline_continue.json
"""

# === CELL 1: Setup ===
import sys, json, pathlib, logging, hashlib, datetime
import torch

DATA_DIR      = "/kaggle/input/datasets/codoes/gemma-triage-data"
OUTPUTS_DIR   = "/kaggle/input/datasets/codoes/gemma-triage-outputs"
BASE_EVAL_DIR = "/kaggle/input/datasets/codoes/gemma-triage-base-eval"

sys.path.append(DATA_DIR)
from eval_utils import build_prompt, parse_triage_code, compute_metrics, print_comparison_report

cfg = json.loads(pathlib.Path(f"{DATA_DIR}/pipeline_config.json").read_text())
cfg["training_data_path"]     = f"{DATA_DIR}/training_dataset.json"
cfg["test_set_path"]          = f"{DATA_DIR}/test_set.json"
cfg["merged_model_path"]      = f"{OUTPUTS_DIR}/merged_model"
cfg["base_eval_results_path"] = f"{BASE_EVAL_DIR}/base_eval_results.json"
cfg["max_seq_length"]         = 2048  # inference only — no training memory constraint

torch.manual_seed(cfg["seed"])
torch.backends.cudnn.deterministic = True
torch.use_deterministic_algorithms(True, warn_only=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_deterministic(fn):
    try:
        return fn()
    except RuntimeError as e:
        if "deterministic" in str(e).lower():
            logger.warning(f"Non-deterministic op: {e}. Falling back.")
            torch.use_deterministic_algorithms(False)
            return fn()
        raise


# === CELL 2: Load base eval results ===
base_results = json.loads(open(cfg["base_eval_results_path"]).read())
print(f"+ Base results loaded | overall_accuracy={base_results['overall_accuracy']:.3f}")


# === CELL 3: Load fine-tuned model ===
from transformers import AutoTokenizer, AutoModelForCausalLM

merged_path = cfg["merged_model_path"]
tokenizer = AutoTokenizer.from_pretrained(merged_path)
tokenizer.model_max_length = cfg["max_seq_length"]

assert (pathlib.Path(merged_path) / "tokenizer.json").exists(), (
    "Tokenizer missing from merged_model/ — was merge_lora.py run successfully?"
)

model = AutoModelForCausalLM.from_pretrained(
    merged_path,
    torch_dtype=torch.float16,
    device_map="auto",
)
model.eval()
print(f"+ Fine-tuned model loaded from {merged_path}")


# === CELL 4: Validate test set ===
test_data  = json.loads(open(cfg["test_set_path"]).read())
test_cases = test_data["cases"]
assert len(test_cases) == 100, f"Expected 100 test cases, got {len(test_cases)}"

# training_dataset.json is a JSON array — use json.loads, NOT line-by-line iteration
train_cases = json.loads(open(cfg["training_data_path"]).read())
first_msg = train_cases[0]["messages"][0]
system_prompt = first_msg["content"] if first_msg["role"] == "system" \
    else first_msg["content"].split("\n\nNow, respond")[0]
print(f"+ Test set loaded | system prompt extracted ({len(system_prompt)} chars)")


# === CELL 5: Run inference (identical to NB1) ===
predictions, labels_list, sources_list = [], [], []
errors = []

for i, case in enumerate(test_cases):
    prompt  = build_prompt(tokenizer, system_prompt, case["description"])
    inputs  = tokenizer(prompt, return_tensors="pt").to(model.device)

    def _generate():
        with torch.no_grad():
            return model.generate(
                **inputs,
                max_new_tokens=256,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )

    output_ids = run_deterministic(_generate)
    new_ids    = output_ids[0][inputs["input_ids"].shape[1]:]
    raw_output = tokenizer.decode(new_ids, skip_special_tokens=True)

    code, error_type = parse_triage_code(raw_output)
    predictions.append(code)
    labels_list.append(case["expected_code"])
    sources_list.append(case.get("source", "generated"))

    if error_type:
        errors.append({"id": case["id"], "raw": raw_output, "error": error_type})

    if (i + 1) % 10 == 0:
        print(f"  {i+1}/100 done")

print(f"+ Inference complete | parse errors: {len(errors)}")


# === CELL 6: Compute metrics ===
import transformers

metrics = compute_metrics(predictions, labels_list, sources_list)
config_str = json.dumps(model.config.to_dict(), sort_keys=True)
model_hash = "sha256:" + hashlib.sha256(config_str.encode()).hexdigest()[:16]

parse_error_counts = {"malformed_json": 0, "missing_key": 0, "invalid_code": 0}
for e in errors:
    parse_error_counts[e["error"]] = parse_error_counts.get(e["error"], 0) + 1

ft_results = {
    "model": cfg["model_id"],
    "model_transformers_version": transformers.__version__,
    "model_config_hash": model_hash,
    "stage": "finetuned",
    "seed": cfg["seed"],
    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    **metrics,
    "parse_errors": parse_error_counts,
}


# === CELL 7: Comparison report + regression check ===
print_comparison_report(
    base_results, ft_results,
    threshold_critical=cfg["f1_drop_threshold_critical"],
    threshold_other=cfg["f1_drop_threshold_other"],
)

export_allowed = True
for cls in ["RED", "BLACK"]:
    base_f1 = base_results["per_class"][cls]["f1"]
    ft_f1   = ft_results["per_class"][cls]["f1"]
    if ft_f1 < base_f1 - cfg["f1_drop_threshold_critical"]:
        print(f"\nBLOCKING REGRESSION on {cls}: "
              f"base={base_f1:.3f} -> finetuned={ft_f1:.3f} "
              f"(drop={base_f1-ft_f1:.3f} > threshold={cfg['f1_drop_threshold_critical']})")
        export_allowed = False


# === CELL 8: Save outputs ===
out = pathlib.Path("/kaggle/working")
(out / "finetuned_eval_results.json").write_text(json.dumps(ft_results, indent=2))
(out / "finetuned_eval_errors.json").write_text(json.dumps(errors, indent=2))
(out / "pipeline_continue.json").write_text(
    json.dumps({"export_allowed": export_allowed}, indent=2)
)

if export_allowed:
    print("\n+ pipeline_continue.json -> export_allowed=true")
    print("  -> Commit outputs as dataset: gemma-triage-finetuned-eval")
    print("  -> Proceed to Notebook 4")
else:
    print("\nSTOP. pipeline_continue.json -> export_allowed=false")
    print("  -> Investigate RED/BLACK regression before running NB4.")
    print("  -> Check loss_curve.png for overfitting. Consider reducing learning rate.")
