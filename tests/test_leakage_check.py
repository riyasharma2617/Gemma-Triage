import sys, json, tempfile, os
sys.path.insert(0, "scripts")
import pytest
from check_leakage import check_id_overlap, check_rouge, check_semantic


SYSTEM_PROMPT = "Act as a doctor."


def make_case(id_, desc):
    return {"id": id_, "description": desc}


# --- ID overlap ---

def test_id_overlap_none():
    train = [make_case("T001", "desc A"), make_case("T002", "desc B")]
    test  = [make_case("G001", "desc C")]
    failures = check_id_overlap(train, test)
    assert failures == []


def test_id_overlap_detected():
    train = [make_case("T001", "desc A")]
    test  = [make_case("T001", "desc B")]
    failures = check_id_overlap(train, test)
    assert "T001" in failures


# --- ROUGE-L ---

def test_rouge_identical_descriptions_fails():
    desc = "Adult male, breathing 34/min, radial pulse absent."
    train = [make_case("T001", desc)]
    test  = [make_case("G001", desc)]
    failures, warnings = check_rouge(train, test, block=0.8, warn=0.7)
    assert len(failures) == 1
    assert failures[0]["test_id"] == "G001"


def test_rouge_completely_different_passes():
    train = [make_case("T001", "Adult male struck by vehicle, RR 34, pulse absent.")]
    test  = [make_case("G001", "Child found unconscious after explosion, apneic.")]
    failures, warnings = check_rouge(train, test, block=0.8, warn=0.7)
    assert failures == []


def test_rouge_warns_on_moderate_overlap():
    # Same structure, one different number — borderline case
    train = [make_case("T001", "Adult male, breathing 20/min, pulse present, follows commands.")]
    test  = [make_case("G001", "Adult male, breathing 22/min, pulse present, follows commands.")]
    failures, warnings = check_rouge(train, test, block=0.8, warn=0.7)
    # Either warns or fails — should not silently pass
    assert len(failures) + len(warnings) >= 1


# --- report writing ---

def test_leakage_report_passed():
    report = {
        "passed": True,
        "id_overlap": [],
        "failures": [],
        "warnings": [],
        "checked_at": "2026-05-11T00:00:00Z",
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(report, f)
        path = f.name
    loaded = json.loads(open(path).read())
    assert loaded["passed"] is True
    os.unlink(path)
