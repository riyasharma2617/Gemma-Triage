"""Split curated data into training_dataset.jsonl (396) and test_set.json (25/class = 100).

Outputs:
  01_data/curated/training_dataset.jsonl  -- chat format, used by NB2 fine-tuning
  01_data/test_set.json                   -- cases-wrapper format, used by NB1/NB3/NB4

Deletes the stale train.jsonl and test.jsonl if they exist.
"""
import json, random
from collections import defaultdict
from pathlib import Path

SEED = 42
TEST_PER_CLASS = 25

HERE = Path(__file__).parent
ROOT = HERE.parent.parent

CURATED_JSON  = HERE / "curated.json"
CHAT_JSONL    = HERE / "training_dataset.jsonl"
TRAIN_OUT     = HERE / "training_dataset.jsonl"   # overwritten in-place
TEST_OUT      = ROOT / "01_data" / "test_set.json"

random.seed(SEED)

# --- load both representations ---
flat_by_id = {
    r["id"]: r
    for r in json.loads(CURATED_JSON.read_text(encoding="utf-8"))
}

chat_by_id = {}
for line in CHAT_JSONL.read_text(encoding="utf-8").splitlines():
    if line.strip():
        rec = json.loads(line)
        chat_by_id[rec["metadata"]["id"]] = rec

assert set(flat_by_id) == set(chat_by_id), (
    f"ID mismatch between curated.json ({len(flat_by_id)}) "
    f"and training_dataset.jsonl ({len(chat_by_id)})"
)

# --- stratified sample: exactly TEST_PER_CLASS per label ---
buckets: dict[str, list] = defaultdict(list)
for id_, rec in flat_by_id.items():
    buckets[rec["expected_code"]].append(id_)

test_ids: set[str] = set()
for label, ids in sorted(buckets.items()):
    available = len(ids)
    assert available >= TEST_PER_CLASS, (
        f"Class {label} has only {available} examples — need {TEST_PER_CLASS} for test"
    )
    random.shuffle(ids)
    test_ids.update(ids[:TEST_PER_CLASS])

train_ids = sorted(set(flat_by_id) - test_ids)
test_ids_sorted = sorted(test_ids)

# --- write test_set.json (cases-wrapper format) ---
cases = [
    {
        "id":            flat_by_id[id_]["id"],
        "description":   flat_by_id[id_]["description"],
        "expected_code": flat_by_id[id_]["expected_code"],
        "source":        flat_by_id[id_].get("source", "curated"),
    }
    for id_ in test_ids_sorted
]
TEST_OUT.write_text(json.dumps({"cases": cases}, indent=2, ensure_ascii=False), encoding="utf-8")

# --- write training_dataset.jsonl (chat format, non-test records) ---
train_records = [chat_by_id[id_] for id_ in train_ids]
random.shuffle(train_records)
TRAIN_OUT.write_text(
    "\n".join(json.dumps(r, ensure_ascii=False) for r in train_records),
    encoding="utf-8",
)

# --- remove stale 60/40 files if present ---
for stale in (HERE / "train.jsonl", HERE / "test.jsonl"):
    if stale.exists():
        stale.unlink()
        print(f"Removed stale file: {stale.name}")

# --- summary ---
from collections import Counter
train_labels = Counter(chat_by_id[id_]["metadata"]["label"] for id_ in train_ids)
test_labels  = Counter(flat_by_id[id_]["expected_code"]     for id_ in test_ids)
all_labels   = sorted(train_labels | test_labels)

print(f"\nTotal  : {len(flat_by_id)}")
print(f"Train  : {len(train_ids)}  -> 01_data/curated/training_dataset.jsonl")
print(f"Test   : {len(test_ids)}   -> 01_data/test_set.json")
print()
print(f"{'Label':<8} {'Train':>6} {'Test':>6} {'Total':>7}")
print("-" * 30)
for label in all_labels:
    tr = train_labels[label]
    te = test_labels[label]
    print(f"{label:<8} {tr:>6} {te:>6} {tr+te:>7}")

print()
print("test_set.json format check:")
loaded = json.loads(TEST_OUT.read_text(encoding="utf-8"))
assert "cases" in loaded
assert len(loaded["cases"]) == TEST_PER_CLASS * len(all_labels)
first = loaded["cases"][0]
for field in ("id", "description", "expected_code", "source"):
    assert field in first, f"Missing field: {field}"
print(f"  OK — {len(loaded['cases'])} cases, fields: {list(first.keys())}")
