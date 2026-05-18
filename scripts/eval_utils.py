"""Shared evaluation utilities for NB1 and NB3.

Both notebooks import this via:
    import sys; sys.path.append("/kaggle/input/datasets/codoes/gemma-triage-data")
    from eval_utils import build_prompt, parse_triage_code, compute_metrics, print_comparison_report
"""
from __future__ import annotations
import json
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix as sk_confusion_matrix

VALID_CODES = {"RED", "YELLOW", "GREEN", "BLACK"}
LABEL_ORDER = ["RED", "YELLOW", "GREEN", "BLACK"]


def build_prompt(tokenizer, system_prompt: str, description: str) -> str:
    """Build inference prompt with system prompt merged into user turn.

    System prompt goes in the user turn (not a separate 'system' role) to match
    how the training data was formatted during fine-tuning.
    """
    messages = [{"role": "user", "content": f"{system_prompt}\n\n{description}"}]
    return tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )


def parse_triage_code(raw_output: str) -> tuple[str, str | None]:
    """Parse triage_code from model JSON output.

    Returns:
        (code, None)             on success — code is one of RED/YELLOW/GREEN/BLACK
        ("PARSE_ERROR", reason)  on failure — reason is malformed_json/missing_key/invalid_code
    """
    try:
        parsed = json.loads(raw_output)
        code = parsed["patient"]["triage_code"]
        if code not in VALID_CODES:
            return "PARSE_ERROR", "invalid_code"
        return code, None
    except json.JSONDecodeError:
        return "PARSE_ERROR", "malformed_json"
    except KeyError:
        return "PARSE_ERROR", "missing_key"


def compute_metrics(
    predictions: list[str],
    labels: list[str],
    sources: list[str],
) -> dict:
    """Compute classification metrics.

    Args:
        predictions: predicted codes; may include "PARSE_ERROR"
        labels:      ground-truth codes (always a valid code)
        sources:     "curated" or "generated" per case
    """
    precision, recall, f1, support = precision_recall_fscore_support(
        labels, predictions,
        labels=LABEL_ORDER,
        average=None,
        zero_division=0,
    )
    per_class = {
        cls: {
            "precision": round(float(precision[i]), 4),
            "recall":    round(float(recall[i]),    4),
            "f1":        round(float(f1[i]),        4),
            "support":   int(support[i]),
        }
        for i, cls in enumerate(LABEL_ORDER)
    }

    overall_acc = sum(p == l for p, l in zip(predictions, labels)) / len(labels)
    macro_f1 = sum(v["f1"] for v in per_class.values()) / 4

    cm = sk_confusion_matrix(labels, predictions, labels=LABEL_ORDER).tolist()

    curated_pairs   = [(p == l) for p, l, s in zip(predictions, labels, sources) if s == "curated"]
    generated_pairs = [(p == l) for p, l, s in zip(predictions, labels, sources) if s == "generated"]
    curated_acc   = sum(curated_pairs)   / len(curated_pairs)   if curated_pairs   else 0.0
    generated_acc = sum(generated_pairs) / len(generated_pairs) if generated_pairs else 0.0

    return {
        "overall_accuracy":   round(float(overall_acc),   4),
        "macro_f1":           round(float(macro_f1),      4),
        "per_class":          per_class,
        "confusion_matrix":   cm,
        "curated_accuracy":   round(float(curated_acc),   4),
        "generated_accuracy": round(float(generated_acc), 4),
    }


def print_comparison_report(
    base_results: dict,
    ft_results: dict,
    threshold_critical: float = 0.01,
    threshold_other: float = 0.02,
) -> None:
    """Print side-by-side comparison. Flags REGRESSION if F1 drops."""
    print("\n=== Gemma Triage — Base vs Fine-tuned ===\n")
    header = f"{'Class':<8} {'Base F1':>8} {'FT F1':>8} {'Delta':>8}  Note"
    print(header)
    print("-" * len(header))

    for cls in LABEL_ORDER:
        base_f1 = base_results["per_class"][cls]["f1"]
        ft_f1   = ft_results["per_class"][cls]["f1"]
        delta   = ft_f1 - base_f1
        threshold = threshold_critical if cls in {"RED", "BLACK"} else threshold_other
        note = ""
        if delta < -threshold:
            note = f"REGRESSION (threshold {threshold})"
        elif cls in {"RED", "BLACK"}:
            note = f"critical (threshold {threshold})"
        print(f"{cls:<8} {base_f1:>8.3f} {ft_f1:>8.3f} {delta:>+8.3f}  {note}")

    print()
    print(f"Overall accuracy:  base={base_results['overall_accuracy']:.3f}  "
          f"finetuned={ft_results['overall_accuracy']:.3f}")
    print(f"Macro F1:          base={base_results['macro_f1']:.3f}  "
          f"finetuned={ft_results['macro_f1']:.3f}")
    print(f"\nCurated edge cases (hand-authored): "
          f"base={base_results['curated_accuracy']:.3f}  "
          f"finetuned={ft_results['curated_accuracy']:.3f}")
    print(f"Generated cases   (programmatic):   "
          f"base={base_results['generated_accuracy']:.3f}  "
          f"finetuned={ft_results['generated_accuracy']:.3f}")
