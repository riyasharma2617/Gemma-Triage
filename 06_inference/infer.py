"""
Notebook 5 — Interactive Inference
Kaggle inputs required:
  - gemma-triage-data     (eval_utils.py, pipeline_config.json, training_dataset.json)
  - gemma-triage-outputs  (merged_model/)
"""

# === CELL 1: Install ===
# !pip install -q git+https://github.com/huggingface/transformers.git


# === CELL 2: Setup ===
import sys, json, pathlib, re, torch

DATA_DIR    = "/kaggle/input/datasets/codoes/gemma-triage-data"
OUTPUTS_DIR = "/kaggle/input/datasets/codoes/gemma-triage-outputs"
MODEL_DIR   = f"{OUTPUTS_DIR}/merged_model"

sys.path.append(DATA_DIR)
from eval_utils import build_prompt, parse_triage_code

cfg = json.loads(pathlib.Path(f"{DATA_DIR}/pipeline_config.json").read_text())
print(f"+ Setup complete | model={MODEL_DIR}")


# === CELL 3: Load model ===
from transformers import AutoTokenizer, AutoModelForCausalLM

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
tokenizer.model_max_length = 2048

model = AutoModelForCausalLM.from_pretrained(
    MODEL_DIR,
    torch_dtype=torch.float16,
    device_map="auto",
)
model.eval()
print(f"+ Model loaded | VRAM: {torch.cuda.memory_allocated()/1e9:.1f} GB")


# === CELL 4: Load system prompt ===
train_data  = json.loads(open(f"{DATA_DIR}/training_dataset.json").read())
first_msg   = train_data[0]["messages"][0]
system_prompt = (
    first_msg["content"] if first_msg["role"] == "system"
    else first_msg["content"].split("\n\nNow, respond")[0]
)
print(f"+ System prompt loaded ({len(system_prompt)} chars)")


# === CELL 5: Inference function ===
def _extract_json(text: str) -> str:
    """Strip markdown fences and extract the first {...} block."""
    text = re.sub(r"```(?:json)?", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group() if match else text


def triage(description: str) -> dict:
    """Run START triage on a patient description. Returns result dict."""
    prompt = build_prompt(tokenizer, system_prompt, description)
    inputs = tokenizer(
        prompt, return_tensors="pt", truncation=True, max_length=2048
    ).to(model.device)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=300,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )

    new_ids    = output_ids[0][inputs["input_ids"].shape[1]:]
    raw_output = tokenizer.decode(new_ids, skip_special_tokens=True).strip()

    # Try direct parse first, then fall back to JSON extraction
    code, error = parse_triage_code(raw_output)
    if error:
        cleaned    = _extract_json(raw_output)
        code, error = parse_triage_code(cleaned)
        raw_output  = cleaned if not error else raw_output

    result = {"code": code, "error": error, "raw": raw_output}
    if not error:
        result["parsed"] = json.loads(raw_output)
    return result


def print_result(description: str, result: dict) -> None:
    """Pretty-print a triage result."""
    COLOR = {"RED": "\033[91m", "YELLOW": "\033[93m", "GREEN": "\033[92m",
             "BLACK": "\033[90m", "PARSE_ERROR": "\033[95m"}
    RESET = "\033[0m"
    code  = result["code"]
    color = COLOR.get(code, "")

    print(f"\n{'─'*60}")
    print(f"Patient: {description}")
    print(f"{'─'*60}")
    if result.get("parsed"):
        p = result["parsed"]["patient"]
        print(f"Triage Code : {color}{code}{RESET}")
        print(f"Reasoning   : {p.get('reasoning', 'N/A')}")
        if p.get("missing_info"):
            print(f"Missing info: {p['missing_info']}")
        if p.get("follow_up_question"):
            print(f"Follow-up   : {p['follow_up_question']}")
    else:
        print(f"Triage Code : {color}{code}{RESET}  [parse error: {result['error']}]")
        print(f"Raw output  : {result['raw'][:200]}")
    print(f"{'─'*60}\n")


# === CELL 6: Quick smoke test (4 representative cases) ===
SMOKE_TESTS = [
    ("T_RED",    "Adult male, struck by vehicle. Not walking. Breathing 34/min, radial pulse absent, cap refill 4s."),
    ("T_YELLOW", "Adult female, lying down. Breathing 20/min, radial pulse present, cap refill 1.5s, follows commands."),
    ("T_GREEN",  "Adult female, walking independently with minor arm laceration and stable breathing."),
    ("T_BLACK",  "Child, 8 years old. Apneic after airway repositioning. No detectable pulse."),
]

print("=== Smoke Test ===")
for label, desc in SMOKE_TESTS:
    r = triage(desc)
    status = "OK" if r["code"] == label.split("_")[1] else f"WRONG (got {r['code']})"
    print(f"  {label}: {status}")


# === CELL 7: Single patient input ===
# ── Edit PATIENT_DESCRIPTION to test your own case ──────────────────────────
PATIENT_DESCRIPTION = """
Adult male, 40s. Found on the ground after building collapse. Not walking.
Breathing approximately 28 breaths per minute. Radial pulse weak but present,
cap refill 3 seconds. Eyes open, responds to voice, confused.
"""
# ────────────────────────────────────────────────────────────────────────────

result = triage(PATIENT_DESCRIPTION.strip())
print_result(PATIENT_DESCRIPTION.strip(), result)


# === CELL 8: Batch input (list of descriptions) ===
# Add as many as you want
BATCH = [
    "Elderly woman, walking slowly but independently. Minor bruising on arms.",
    "Teen male, not breathing after airway repositioning, no pulse found.",
    "Adult, breathing 12/min, weak radial pulse, cap refill 2.5s, unresponsive to commands.",
    "Pregnant woman, walking, crying, asking for help. Breathing normal.",
]

print("=== Batch Results ===")
for desc in BATCH:
    r = triage(desc)
    reasoning = r["parsed"]["patient"]["reasoning"] if r.get("parsed") else r["error"]
    print(f"[{r['code']:<11}] {desc[:65]}")
    print(f"             → {reasoning[:90]}")
    print()
