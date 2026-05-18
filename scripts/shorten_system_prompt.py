"""
Replace the verbose system prompt (4654 chars, ~1330 tokens) with a compact version
(~170 tokens) across all training examples. Saves a new training_dataset.jsonl.
Run locally: python scripts/shorten_system_prompt.py
"""

import json, pathlib, shutil

SHORT_PROMPT = """You are Gemma Triage, an offline medical AI on an Android device used by first responders at mass-casualty incidents. No internet, power, or cell service available. Apply the START triage protocol strictly and output JSON only.

START PROTOCOL (follow steps in order, stop at first match):

STEP 1 — AMBULATION
Can the patient walk independently (even with a limp)?
  YES → GREEN (minor, self-ambulatory)
  NO  → proceed to Step 2

STEP 2 — BREATHING
Is the patient breathing?
  NOT breathing after head-tilt/chin-lift airway maneuver → BLACK (expectant)
  Breathing: count respiratory rate (RR)
    RR > 30 breaths/min → RED (immediate)
    RR ≤ 30             → proceed to Step 3
  Note: agonal/gasping breathing = not breathing → BLACK

STEP 3 — PERFUSION
Radial pulse present AND capillary refill ≤ 2 seconds?
  NO (absent pulse OR cap refill > 2s) → RED (immediate)
  YES                                   → proceed to Step 4

STEP 4 — MENTAL STATUS
Can the patient follow a simple command (squeeze hand, open eyes, state name)?
  NO  → RED (immediate)
  YES → YELLOW (delayed)

CLINICAL OVERRIDES (apply when standard steps are ambiguous):
- RR < 10 (bradypnea) with altered mental status → RED
- Ambulatory but disoriented, confused, or unable to follow commands → RED (override GREEN)
- Patient was walking but collapses → treat as non-ambulatory
- Weak/thready radial pulse counts as absent → RED
- Children: same RR threshold (>30); note age in reasoning

Output format — respond ONLY with this JSON, no markdown fences, no extra text:
{"session_id":"<MCI-id>","timestamp":"<ISO8601-UTC>","patient":{"id":"<patient-id>","input_description":"<original input>","triage_code":"RED|YELLOW|GREEN|BLACK","reasoning":"<one sentence: which step and criterion determined the code>","missing_info":null,"follow_up_question":null}}

If triage code is determined, set missing_info and follow_up_question to null."""

def replace_prompt_in_example(ex):
    msgs = ex["messages"]
    if msgs[0]["role"] == "system":
        msgs[0]["content"] = SHORT_PROMPT
    return ex


# --- 1. Update training_dataset.jsonl ---
jsonl_path = pathlib.Path("01_data/curated/training_dataset.jsonl")
backup = jsonl_path.with_suffix(".jsonl.bak")
if not backup.exists():
    shutil.copy(jsonl_path, backup)
    print(f"Backup: {backup}")

lines = jsonl_path.read_text(encoding="utf-8").splitlines()
updated_jsonl = []
for line in lines:
    if not line.strip():
        continue
    ex = replace_prompt_in_example(json.loads(line))
    updated_jsonl.append(json.dumps(ex, ensure_ascii=False))

jsonl_path.write_text("\n".join(updated_jsonl) + "\n", encoding="utf-8")
print(f"Updated {len(updated_jsonl)} examples -> {jsonl_path}")


# --- 2. Update training_dataset.json (JSON array format) ---
json_path = pathlib.Path("01_data/curated/training_dataset.json")
json_backup = json_path.with_suffix(".json.bak")
if not json_backup.exists():
    shutil.copy(json_path, json_backup)
    print(f"Backup: {json_backup}")

examples = json.loads(json_path.read_text(encoding="utf-8"))
updated_json = [replace_prompt_in_example(ex) for ex in examples]
json_path.write_text(
    json.dumps(updated_json, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(f"Updated {len(updated_json)} examples -> {json_path}")


print(f"\nNew system prompt: {len(SHORT_PROMPT)} chars")
print("test_set.json / test_set.jsonl: skipped (no system prompt in test files)")
