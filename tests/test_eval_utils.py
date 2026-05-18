import sys
sys.path.insert(0, "scripts")
import pytest
from eval_utils import build_prompt, parse_triage_code, compute_metrics


# --- build_prompt ---

def test_build_prompt_contains_system_and_description(mock_tokenizer):
    result = build_prompt(mock_tokenizer, "SYSTEM", "patient fell")
    assert "SYSTEM" in result
    assert "patient fell" in result


def test_build_prompt_system_in_user_turn(mock_tokenizer):
    result = build_prompt(mock_tokenizer, "SYSTEM", "patient fell")
    # system prompt must NOT appear as a separate "system" role line
    lines = result.split("\n")
    assert not any(line.startswith("system:") for line in lines)
    # must appear inside the user turn
    user_lines = [l for l in lines if l.startswith("user:")]
    assert any("SYSTEM" in l for l in user_lines)


# --- parse_triage_code ---

@pytest.mark.parametrize("code", ["RED", "YELLOW", "GREEN", "BLACK"])
def test_parse_valid_code(code):
    raw = f'{{"patient": {{"triage_code": "{code}"}}}}'
    result, error = parse_triage_code(raw)
    assert result == code
    assert error is None


def test_parse_full_response_structure():
    raw = ('{"session_id": "X", "patient": {"id": "T1", "triage_code": "RED", '
           '"reasoning": "RR>30", "missing_info": null, "follow_up_question": null}}')
    result, error = parse_triage_code(raw)
    assert result == "RED"
    assert error is None


def test_parse_malformed_json():
    result, error = parse_triage_code("not json {{{")
    assert result == "PARSE_ERROR"
    assert error == "malformed_json"


def test_parse_missing_patient_key():
    result, error = parse_triage_code('{"session_id": "X"}')
    assert result == "PARSE_ERROR"
    assert error == "missing_key"


def test_parse_missing_triage_code_key():
    result, error = parse_triage_code('{"patient": {"reasoning": "test"}}')
    assert result == "PARSE_ERROR"
    assert error == "missing_key"


def test_parse_invalid_code_value():
    result, error = parse_triage_code('{"patient": {"triage_code": "PURPLE"}}')
    assert result == "PARSE_ERROR"
    assert error == "invalid_code"


def test_parse_empty_string():
    result, error = parse_triage_code("")
    assert result == "PARSE_ERROR"
    assert error == "malformed_json"


# --- compute_metrics ---

def test_compute_metrics_perfect(perfect_predictions):
    preds, labels, sources = perfect_predictions
    result = compute_metrics(preds, labels, sources)
    assert result["overall_accuracy"] == 1.0
    assert result["macro_f1"] == 1.0
    for cls in ["RED", "YELLOW", "GREEN", "BLACK"]:
        assert result["per_class"][cls]["f1"] == 1.0
    assert result["curated_accuracy"] == 1.0
    assert result["generated_accuracy"] == 1.0


def test_compute_metrics_all_wrong():
    labels = ["RED", "GREEN", "YELLOW", "BLACK"]
    preds  = ["GREEN", "RED", "BLACK", "YELLOW"]
    sources = ["generated"] * 4
    result = compute_metrics(preds, labels, sources)
    assert result["overall_accuracy"] == 0.0


def test_compute_metrics_parse_error_counts_as_wrong():
    labels  = ["RED", "RED", "YELLOW"]
    preds   = ["RED", "PARSE_ERROR", "YELLOW"]
    sources = ["generated"] * 3
    result = compute_metrics(preds, labels, sources)
    assert abs(result["overall_accuracy"] - 2/3) < 1e-3


def test_compute_metrics_curated_vs_generated_split():
    labels  = ["RED",  "RED",  "GREEN",   "GREEN"]
    preds   = ["RED",  "YELLOW", "GREEN", "GREEN"]
    sources = ["curated", "curated", "generated", "generated"]
    result = compute_metrics(preds, labels, sources)
    assert result["curated_accuracy"]   == 0.5
    assert result["generated_accuracy"] == 1.0


def test_compute_metrics_returns_required_keys(perfect_predictions):
    preds, labels, sources = perfect_predictions
    result = compute_metrics(preds, labels, sources)
    for key in ["overall_accuracy", "macro_f1", "per_class",
                "confusion_matrix", "curated_accuracy", "generated_accuracy"]:
        assert key in result
    for cls in ["RED", "YELLOW", "GREEN", "BLACK"]:
        assert cls in result["per_class"]
        for sub in ["precision", "recall", "f1", "support"]:
            assert sub in result["per_class"][cls]


def test_confusion_matrix_shape(perfect_predictions):
    preds, labels, sources = perfect_predictions
    result = compute_metrics(preds, labels, sources)
    cm = result["confusion_matrix"]
    assert len(cm) == 4
    assert all(len(row) == 4 for row in cm)
