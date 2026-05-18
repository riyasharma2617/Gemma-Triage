"""
Notebook 1 — Base Model Evaluation
Kaggle inputs required:
  - gemma-4-e2b-it  (Kaggle model: google/gemma-4/transformers/gemma-4-e2b-it/1)
  - gemma-triage-data  (dataset: training_dataset.json, test_set.json,
                         leakage_report.json, eval_utils.py, pipeline_config.json)
Output dataset: gemma-triage-base-eval
  - base_eval_results.json
  - base_eval_errors.json
"""

# === CELL 1: Setup ===
import sys, json, pathlib, logging, hashlib, datetime
import torch

DATA_DIR  = "/kaggle/input/datasets/codoes/gemma-triage-data"
MODEL_DIR = "/kaggle/input/models/google/gemma-4/transformers/gemma-4-e2b-it/1"

sys.path.append(DATA_DIR)
from eval_utils import build_prompt, parse_triage_code, compute_metrics

cfg = json.loads(pathlib.Path(f"{DATA_DIR}/pipeline_config.json").read_text())
cfg["training_data_path"] = f"{DATA_DIR}/training_dataset.json"
cfg["test_set_path"]      = f"{DATA_DIR}/test_set.json"
cfg["model_kaggle_path"]  = MODEL_DIR

torch.manual_seed(cfg["seed"])
torch.backends.cudnn.deterministic = True
torch.use_deterministic_algorithms(True, warn_only=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_deterministic(fn):
    """Run fn; fall back gracefully if a Gemma op is not deterministic."""
    try:
        return fn()
    except RuntimeError as e:
        if "deterministic" in str(e).lower():
            logger.warning(f"Non-deterministic op: {e}. Falling back.")
            torch.use_deterministic_algorithms(False)
            return fn()
        raise


# === CELL 2: Validate inputs ===
report_path = f"{DATA_DIR}/leakage_report.json"
assert pathlib.Path(report_path).exists(), (
    "leakage_report.json not found in gemma-triage-data — run scripts/check_leakage.py first"
)
report = json.loads(open(report_path).read())
assert report["passed"], f"Leakage check not passed: {report['failures']}"

# training_dataset.json is a JSON array (Kaggle converts .jsonl to JSON array)
train_cases = json.loads(open(cfg["training_data_path"]).read())
test_data   = json.loads(open(cfg["test_set_path"]).read())
test_cases  = test_data["cases"]

assert len(train_cases) >= 390, f"Expected ~496 training examples, got {len(train_cases)}"
assert len(test_cases)  == 100, f"Expected 100 test cases, got {len(test_cases)}"
print(f"+ Inputs validated: {len(train_cases)} train | {len(test_cases)} test")


# === CELL 3: Load model ===
import transformers
from transformers import AutoTokenizer, AutoModelForCausalLM

tokenizer = AutoTokenizer.from_pretrained(cfg["model_kaggle_path"])
tokenizer.model_max_length = cfg["max_seq_length"]

assert "user" in tokenizer.chat_template, (
    f"Unexpected chat template — expected 'user' role. Got: {tokenizer.chat_template[:100]}"
)

model = AutoModelForCausalLM.from_pretrained(
    cfg["model_kaggle_path"],
    torch_dtype=torch.float16,
    device_map="auto",
)
model.eval()

config_str = json.dumps(model.config.to_dict(), sort_keys=True)
model_hash = "sha256:" + hashlib.sha256(config_str.encode()).hexdigest()[:16]
print(f"+ Model loaded | transformers={transformers.__version__} | hash={model_hash}")


# === CELL 4: Extract system prompt ===
first_msg = train_cases[0]["messages"][0]
if first_msg["role"] == "system":
    system_prompt = first_msg["content"]
else:
    system_prompt = first_msg["content"].split("\n\nNow, respond")[0]
print(f"+ System prompt extracted ({len(system_prompt)} chars)")


# === CELL 5: Run inference ===
predictions, labels_list, sources_list = [], [], []
errors = []

for i, case in enumerate(test_cases):
    prompt   = build_prompt(tokenizer, system_prompt, case["description"])
    inputs   = tokenizer(prompt, return_tensors="pt").to(model.device)

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


# === CELL 6: Compute metrics and save ===
metrics = compute_metrics(predictions, labels_list, sources_list)

parse_error_counts = {"malformed_json": 0, "missing_key": 0, "invalid_code": 0}
for e in errors:
    parse_error_counts[e["error"]] = parse_error_counts.get(e["error"], 0) + 1

results = {
    "model": cfg["model_id"],
    "model_transformers_version": transformers.__version__,
    "model_config_hash": model_hash,
    "stage": "base",
    "seed": cfg["seed"],
    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    **metrics,
    "parse_errors": parse_error_counts,
}

out_dir = pathlib.Path("/kaggle/working")
(out_dir / "base_eval_results.json").write_text(json.dumps(results, indent=2))
(out_dir / "base_eval_errors.json").write_text(json.dumps(errors, indent=2))

print("\n=== Base Model Results ===")
print(f"Overall accuracy: {results['overall_accuracy']:.3f}")
print(f"Macro F1:         {results['macro_f1']:.3f}")
for cls in ["RED", "YELLOW", "GREEN", "BLACK"]:
    pc = results["per_class"][cls]
    print(f"  {cls:<7} F1={pc['f1']:.3f}  P={pc['precision']:.3f}  R={pc['recall']:.3f}")
print(f"Curated accuracy:   {results['curated_accuracy']:.3f}")
print(f"Generated accuracy: {results['generated_accuracy']:.3f}")
print(f"Parse errors: {parse_error_counts}")
print(f"\n+ Results saved to /kaggle/working/")
print("  -> Commit as output dataset: gemma-triage-base-eval")
