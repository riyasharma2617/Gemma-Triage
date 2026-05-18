"""Script 0 — data leakage check. Run locally before starting Kaggle notebooks.

Usage:
    python scripts/check_leakage.py \
        --train 01_data/curated/training_dataset.jsonl \
        --test  01_data/test_set.json \
        --config pipeline_config.json \
        --out   01_data/leakage_report.json

Writes leakage_report.json. Upload this to the gemma-triage-data Kaggle dataset.
"""
from __future__ import annotations
import argparse, json, datetime


def check_id_overlap(train_cases: list[dict], test_cases: list[dict]) -> list[str]:
    train_ids = {c["id"] for c in train_cases}
    test_ids  = {c["id"] for c in test_cases}
    return sorted(train_ids & test_ids)


def check_rouge(
    train_cases: list[dict],
    test_cases: list[dict],
    block: float = 0.8,
    warn: float = 0.7,
) -> tuple[list[dict], list[dict]]:
    from rouge_score import rouge_scorer as rs_module
    scorer = rs_module.RougeScorer(["rougeL"], use_stemmer=True)
    failures, warnings = [], []
    for tc in test_cases:
        for tr in train_cases:
            score = scorer.score(
                tc["description"], tr["description"]
            )["rougeL"].fmeasure
            entry = {"test_id": tc["id"], "train_id": tr["id"],
                     "score": round(score, 4), "check": "rouge"}
            if score > block:
                failures.append(entry)
            elif score > warn:
                warnings.append(entry)
    return failures, warnings


def check_semantic(
    train_cases: list[dict],
    test_cases: list[dict],
    warn_threshold: float = 0.90,
) -> list[dict]:
    """Warning-only semantic check using sentence embeddings."""
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
    except ImportError:
        print("sentence-transformers not installed — skipping semantic check")
        return []

    model = SentenceTransformer("all-MiniLM-L6-v2")
    train_descs = [c["description"] for c in train_cases]
    test_descs  = [c["description"] for c in test_cases]
    train_embs  = model.encode(train_descs, normalize_embeddings=True)
    test_embs   = model.encode(test_descs,  normalize_embeddings=True)
    import numpy as np
    sim_matrix  = test_embs @ train_embs.T

    warnings = []
    for i, tc in enumerate(test_cases):
        for j, tr in enumerate(train_cases):
            if sim_matrix[i, j] > warn_threshold:
                warnings.append({
                    "test_id": tc["id"], "train_id": tr["id"],
                    "score": round(float(sim_matrix[i, j]), 4),
                    "check": "semantic",
                })
    return warnings


def load_train_cases(path: str) -> list[dict]:
    """Load training_dataset.jsonl and extract id + description."""
    cases = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            # description is in the last user message content
            user_content = entry["messages"][-2]["content"] \
                if entry["messages"][-1]["role"] == "assistant" \
                else entry["messages"][-1]["content"]
            cases.append({"id": entry["metadata"]["id"], "description": user_content})
    return cases


def load_test_cases(path: str) -> list[dict]:
    """Load test_set.json and extract id + description."""
    data = json.loads(open(path).read())
    return [{"id": c["id"], "description": c["description"]} for c in data["cases"]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train",  default="01_data/curated/training_dataset.jsonl")
    parser.add_argument("--test",   default="01_data/test_set.json")
    parser.add_argument("--config", default="pipeline_config.json")
    parser.add_argument("--out",    default="01_data/leakage_report.json")
    args = parser.parse_args()

    cfg = json.loads(open(args.config).read())

    print("Loading datasets...")
    train_cases = load_train_cases(args.train)
    test_cases  = load_test_cases(args.test)
    print(f"  Train: {len(train_cases)} cases | Test: {len(test_cases)} cases")

    print("Step 1: Checking ID overlap...")
    id_failures = check_id_overlap(train_cases, test_cases)

    print("Step 2: Checking ROUGE-L overlap...")
    rouge_failures, rouge_warnings = check_rouge(
        train_cases, test_cases,
        block=cfg["leakage_rouge_block"],
        warn=cfg["leakage_rouge_warn"],
    )

    print("Step 3: Checking semantic similarity...")
    semantic_warnings = check_semantic(
        train_cases, test_cases,
        warn_threshold=cfg["leakage_semantic_warn"],
    )

    all_failures = rouge_failures + [{"id": i, "check": "id"} for i in id_failures]
    all_warnings = rouge_warnings + semantic_warnings
    passed = len(all_failures) == 0

    report = {
        "passed": passed,
        "id_overlap": id_failures,
        "failures": all_failures,
        "warnings": all_warnings,
        "checked_at": datetime.datetime.utcnow().isoformat() + "Z",
    }
    with open(args.out, "w") as f:
        json.dump(report, f, indent=2)

    if all_warnings:
        print(f"\n  {len(all_warnings)} warnings (logged but not blocking):")
        for w in all_warnings[:5]:
            print(f"   {w['test_id']} <-> {w['train_id']} score={w['score']} ({w['check']})")

    if not passed:
        print(f"\nx LEAKAGE CHECK FAILED: {len(all_failures)} failures")
        raise SystemExit(1)

    print(f"\n+ Leakage check passed. Report written to {args.out}")
    print("  Upload leakage_report.json to the gemma-triage-data Kaggle dataset.")


if __name__ == "__main__":
    main()
