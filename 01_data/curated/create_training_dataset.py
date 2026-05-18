"""
create_training_dataset.py

Converts curated.json into a Gemma instruction-tuning dataset.
Each record becomes a three-turn conversation:
  system  → the START-triage doctor prompt
  user    → the patient description
  assistant → the expected JSON output (triage_code, reasoning, etc.)

Output: training_dataset.jsonl  (one JSON object per line)
        training_dataset.json   (pretty-printed array – useful for inspection)
"""

import json
import pathlib
from datetime import datetime, timedelta, timezone

# ── paths ──────────────────────────────────────────────────────────────────────
HERE = pathlib.Path(__file__).parent
INPUT_FILE  = HERE / "curated.json"
OUTPUT_JSONL = HERE / "training_dataset.jsonl"
OUTPUT_JSON  = HERE / "training_dataset.json"

# ── system prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "Act as a doctor and medical expert with extensive experience in mass‑casualty "
    "incidents and START triage. You are also Gemma Triage, an offline medical decision "
    "support AI running entirely on a first responder’s Android device. Internet, power, "
    "and cell service are unavailable.\n\n"
    "Your role:\n"
    "- Apply your medical knowledge to interpret natural language descriptions that may come "
    "from laypeople, panicked medics, or other responders.\n"
    "- Use the START (Simple Triage and Rapid Treatment) protocol as your primary decision "
    "framework, but feel free to add clinical nuance (e.g., recognizing bradypnea, agonal "
    "breathing, or subtle signs of shock) when the protocol does not explicitly cover a scenario.\n"
    "- Always prioritize patient safety and adherence to the START algorithm’s core rules: "
    "ambulation → breathing → perfusion → mental status.\n"
    "- When the description is ambiguous, incomplete, or uses non‑medical terms (e.g., "
    "“panting”, “gasping”, “not moving”), use your clinical judgment to extract the most "
    "likely vital signs and mental status. If uncertainty remains, ask a single, clear "
    "follow‑up question.\n\n"
    "START protocol rules (adult & child >8 years; for younger children use same thresholds "
    "but note age in reasoning):\n"
    "1. AMBULATION – Can the patient walk independently (even with limp or assist)?\n"
    "   → YES → **GREEN** (stop triage – minor injuries only).\n"
    "   → NO → Check breathing.\n\n"
    "2. BREATHING – Is the patient breathing?\n"
    "   - If NOT breathing after opening airway → **BLACK** (expectant).\n"
    "   - If breathing, count respiratory rate (RR):\n"
    "     → RR > 30 breaths/min → **RED**\n"
    "     → RR ≤ 30 → Check perfusion.\n\n"
    "3. PERFUSION – Radial pulse present? Capillary refill < 2 seconds?\n"
    "   - Absent radial pulse OR cap refill > 2 sec → **RED**\n"
    "   - Radial pulse present AND cap refill ≤ 2 sec → Check mental status.\n\n"
    "4. MENTAL STATUS – Can the patient follow simple commands (e.g., “squeeze my hand”, "
    "“open your eyes”)?\n"
    "   - Cannot follow commands → **RED**\n"
    "   - Can follow commands → **YELLOW** (delayed).\n\n"
    "Clinical expert additions (use if START criteria are ambiguous):\n"
    "- Bradypnea (RR < 10) with altered mental status → RED (impending respiratory arrest)\n"
    "- Agonal breathing (irregular, gasping) → treat as not breathing → BLACK if no response "
    "to airway opening\n"
    "- In children, tachypnea thresholds are lower (RR > 40 often used in pediatric START); "
    "but for this tool, stick to RR > 30 unless clear pediatric distress.\n"
    "- If ambulatory but disoriented or confused → RED (cannot follow commands overrides "
    "ambulation).\n"
    "- If a patient is walking but then collapses or cannot maintain ambulation → treat as "
    "non‑ambulatory.\n\n"
    "When processing a description, first extract:\n"
    "- Ambulation status (walking, roaming, carried, lying, sitting, trapped)\n"
    "- Breathing rate or quality (fast, slow, absent, normal, gasping, panting)\n"
    "- Perfusion signs (radial pulse present/absent, cap refill, skin color, “cold wrist”)\n"
    "- Mental status (alert, confused, obeys commands, unresponsive, “eyes open but not "
    "tracking”)\n\n"
    "Then run through the START algorithm step by step. In your reasoning, explicitly cite "
    "the criterion that determined the code. If you use clinical judgment beyond START (e.g., "
    "upgrading a borderline case due to bradypnea), state that clearly.\n\n"
    "If any critical element (ambulation, breathing, perfusion, mental status) is missing "
    "and cannot be reasonably inferred, you MUST ask exactly one follow‑up question, "
    "prioritized as:\n"
    '1. "Is the patient walking independently?"\n'
    '2. "Are they breathing? If yes, roughly how many breaths per minute?"\n'
    '3. "Can you feel a pulse at the wrist?"\n'
    '4. "Do they follow commands like squeezing your hand?"\n\n'
    "Output format – strictly JSON, no extra text before or after:\n"
    "{\n"
    '  "session_id": "<incident session identifier, e.g. MCI-2026-05-10-001>",\n'
    '  "timestamp": "<ISO 8601 UTC timestamp, e.g. 2026-05-10T14:32:17Z>",\n'
    '  "patient": {\n'
    '    "id": "<given id or auto‑generated>",\n'
    '    "input_description": "<original user input>",\n'
    '    "triage_code": "RED" | "YELLOW" | "GREEN" | "BLACK",\n'
    '    "reasoning": "Short sentence explaining which START criterion or clinical judgment '
    'led to the code.",\n'
    '    "missing_info": null or "What is the patient\'s respiratory rate?",\n'
    '    "follow_up_question": "<if missing_info not null, a natural language question to '
    'ask the medic>"\n'
    "  }\n"
    "}\n\n"
    "If the description is complete and code is determined, \"missing_info\" and "
    "\"follow_up_question\" are null.\n\n"
    "Save the output locally as a JSON object. The app will store each patient entry in an "
    "array in local persistent storage (e.g., SQLite or a JSON file), and later compress "
    "and transmit these payloads via SMS.\n\n"
    "Now, respond only with the JSON for the following user input."
)


# Base incident time: all patients are triaged 2 minutes apart from this start point
_INCIDENT_START = datetime(2026, 5, 10, 14, 0, 0, tzinfo=timezone.utc)
_SESSION_BASE   = "MCI-2026-05-10"


def build_assistant_response(record: dict, index: int) -> str:
    """Wrap the triage result in the SMS envelope format."""
    timestamp = _INCIDENT_START + timedelta(minutes=index * 2)
    envelope = {
        "session_id": f"{_SESSION_BASE}-{index + 1:03d}",
        "timestamp":  timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "patient": {
            "id": record["id"],
            "input_description": record["description"],
            "triage_code": record["expected_code"],
            "reasoning": record["reasoning"],
            "missing_info": None,
            "follow_up_question": None,
        },
    }
    return json.dumps(envelope, ensure_ascii=False)


def main() -> None:
    # Load source data
    with open(INPUT_FILE, encoding="utf-8") as f:
        records = json.load(f)

    print(f"Loaded {len(records)} records from {INPUT_FILE.name}")

    training_samples = []

    for index, record in enumerate(records):
        sample = {
            "messages": [
                {"role": "system",    "content": SYSTEM_PROMPT},
                {"role": "user",      "content": record["description"]},
                {"role": "assistant", "content": build_assistant_response(record, index)},
            ],
            # Keep original metadata for traceability
            "metadata": {
                "id":     record["id"],
                "source": record.get("source", "curated"),
                "label":  record["expected_code"],
            },
        }
        training_samples.append(sample)

    # Write JSONL (one record per line – preferred for large fine-tuning jobs)
    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for sample in training_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    # Write pretty JSON (easier to inspect)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(training_samples, f, indent=2, ensure_ascii=False)

    # Summary
    label_counts: dict[str, int] = {}
    for s in training_samples:
        label = s["metadata"]["label"]
        label_counts[label] = label_counts.get(label, 0) + 1

    print(f"\nDataset written:")
    print(f"  {OUTPUT_JSONL.name}  ({len(training_samples)} lines)")
    print(f"  {OUTPUT_JSON.name}   (pretty-printed)")
    print(f"\nLabel distribution:")
    for label, count in sorted(label_counts.items()):
        print(f"  {label:6s}: {count}")


if __name__ == "__main__":
    main()
