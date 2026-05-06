#!/usr/bin/env python3
"""
Gemma Triage — Python CLI Demo
Simulates the Android on-device triage pipeline via Gemini API.
Usage:
  python triage_demo.py                    # interactive mode
  python triage_demo.py --batch --file patients.csv  # batch mode
"""

import os
import sys
import json
import argparse
import csv
from pathlib import Path

try:
    import google.generativeai as genai
except ImportError:
    print("ERROR: google-generativeai not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

# ─── ANSI colors ─────────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
RED    = "\033[91m"
YELLOW = "\033[93m"
GREEN  = "\033[92m"
GRAY   = "\033[90m"
CYAN   = "\033[96m"

TRIAGE_COLORS = {
    "RED":    RED,
    "YELLOW": YELLOW,
    "GREEN":  GREEN,
    "BLACK":  GRAY,
    "UNKNOWN": "\033[95m"
}

# ─── Load system prompt ───────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
SYSTEM_PROMPT_PATH = SCRIPT_DIR.parent / "android" / "app" / "src" / "main" / "assets" / "prompts" / "system_prompt.txt"

def load_system_prompt() -> str:
    if SYSTEM_PROMPT_PATH.exists():
        return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
    # fallback inline
    return (
        "You are an emergency triage AI using START protocol. "
        "Respond with valid JSON only. Fields: triageCode, confidence, reasoning, "
        "spokenSummary, immediateSteps, monitoringChecklist, warningSigns, smsPayload."
    )

SYSTEM_PROMPT = load_system_prompt()

# ─── Gemini client setup ─────────────────────────────────────────────────────
def get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: Set GEMINI_API_KEY environment variable.")
        sys.exit(1)
    genai.configure(api_key=api_key)
    return genai

MODEL_NAME = "gemini-2.5-flash-preview-05-20"

# ─── Triage inference ────────────────────────────────────────────────────────
def run_triage(patient_description: str) -> dict:
    client = get_client()
    model = client.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_PROMPT,
        generation_config=client.types.GenerationConfig(
            temperature=0.1,
            max_output_tokens=512,
        )
    )
    response = model.generate_content(patient_description)
    raw = response.text.strip()
    return parse_triage_json(raw)

def parse_triage_json(raw: str) -> dict:
    # Strip code fences if present
    text = raw
    if "```" in text:
        lines = text.split("\n")
        text = "\n".join(l for l in lines if not l.strip().startswith("```"))
    # Find JSON object
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start == -1 or end <= start:
        return {"triageCode": "UNKNOWN", "confidence": 0.0, "reasoning": "Parse failed", "raw": raw,
                "spokenSummary": "", "immediateSteps": [], "smsPayload": "TRG|U|0|PARSE_FAILED"}
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        return {"triageCode": "UNKNOWN", "confidence": 0.0, "reasoning": "JSON decode error", "raw": raw,
                "spokenSummary": "", "immediateSteps": [], "smsPayload": "TRG|U|0|PARSE_FAILED"}

# ─── Follow-up inference ─────────────────────────────────────────────────────
def run_followup(chat_session, question: str) -> str:
    response = chat_session.send_message(question)
    return response.text.strip()

def start_followup_session(patient_description: str, triage_result: dict):
    client = get_client()
    followup_system = (
        f"You are an emergency triage assistant. The patient was assessed as "
        f"{triage_result.get('triageCode', 'UNKNOWN')} using START protocol. "
        f"Initial assessment: {triage_result.get('reasoning', '')}. "
        f"Answer follow-up questions from the first responder concisely and practically. "
        f"Assume resource-constrained field conditions."
    )
    model = client.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=followup_system,
        generation_config=client.types.GenerationConfig(
            temperature=0.3,
            max_output_tokens=768,
        )
    )
    chat = model.start_chat(history=[
        {"role": "user",  "parts": [patient_description]},
        {"role": "model", "parts": [json.dumps(triage_result)]},
    ])
    return chat

# ─── Display ─────────────────────────────────────────────────────────────────
def display_triage(result: dict):
    code  = result.get("triageCode", "UNKNOWN")
    color = TRIAGE_COLORS.get(code, "\033[95m")
    conf  = int(result.get("confidence", 0.0) * 100)

    print(f"\n{color}{BOLD}{'─'*50}{RESET}")
    print(f"{color}{BOLD}  TRIAGE: {code}  ({conf}% confidence){RESET}")
    print(f"{color}{BOLD}{'─'*50}{RESET}")

    if result.get("spokenSummary"):
        print(f"\n{BOLD}Summary:{RESET} {result['spokenSummary']}")

    if result.get("reasoning"):
        print(f"{BOLD}Reasoning:{RESET} {result['reasoning']}")

    steps = result.get("immediateSteps", [])
    if steps:
        print(f"\n{BOLD}Immediate Steps:{RESET}")
        for i, step in enumerate(steps, 1):
            print(f"  {i}. {step}")

    sms = result.get("smsPayload", "")
    if sms:
        print(f"\n{CYAN}{BOLD}SMS Payload ({len(sms)} chars):{RESET} {sms}")

    if "raw" in result:
        print(f"\n{YELLOW}[Raw output — parse failed]:{RESET}\n{result['raw']}")

# ─── Interactive mode ────────────────────────────────────────────────────────
def interactive_mode():
    print(f"\n{BOLD}Gemma Triage — Python Demo{RESET}")
    print("Simulates the Android on-device triage pipeline via Gemini API.")
    print(f"Model: {MODEL_NAME} | Type 'exit' to quit\n")

    patient_num = 0
    while True:
        patient_num += 1
        print(f"{BOLD}─── Patient {patient_num} ───────────────────────────────{RESET}")
        try:
            desc = input("Patient description (or 'exit'): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if desc.lower() in ("exit", "quit", "q"):
            break
        if not desc:
            print("No description entered. Try again.")
            patient_num -= 1
            continue

        print(f"\n{CYAN}Running triage inference...{RESET}")
        try:
            result = run_triage(desc)
        except Exception as e:
            print(f"{RED}ERROR during triage: {e}{RESET}")
            patient_num -= 1
            continue

        display_triage(result)

        # Follow-up loop
        chat = None
        while True:
            try:
                q = input(f"\n{BOLD}Follow-up question (or 'next patient'/'exit'):{RESET} ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                return

            if not q:
                continue
            if q.lower() in ("next patient", "next", "n"):
                break
            if q.lower() in ("exit", "quit", "q"):
                return

            if chat is None:
                chat = start_followup_session(desc, result)

            print(f"\n{CYAN}Follow-up inference...{RESET}")
            try:
                answer = run_followup(chat, q)
                print(f"\n{BOLD}Answer:{RESET} {answer}")
            except Exception as e:
                print(f"{RED}ERROR during follow-up: {e}{RESET}")

# ─── Batch mode ──────────────────────────────────────────────────────────────
def batch_mode(filepath: str):
    results_out = csv.writer(sys.stdout)
    results_out.writerow(["patient_num", "description", "triageCode", "confidence", "reasoning", "smsPayload"])

    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader, 1):
            if not row:
                continue
            desc = row[0].strip()
            if not desc or desc.lower() == "description":
                continue
            try:
                result = run_triage(desc)
                results_out.writerow([
                    i,
                    desc,
                    result.get("triageCode", "UNKNOWN"),
                    result.get("confidence", 0.0),
                    result.get("reasoning", ""),
                    result.get("smsPayload", ""),
                ])
                sys.stdout.flush()
            except Exception as e:
                results_out.writerow([i, desc, "ERROR", 0.0, str(e), ""])
                sys.stdout.flush()

# ─── Entry point ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Gemma Triage CLI Demo")
    parser.add_argument("--batch", action="store_true", help="Batch mode: read from CSV file")
    parser.add_argument("--file",  type=str,           help="CSV file for batch mode (one description per row)")
    args = parser.parse_args()

    if args.batch:
        if not args.file:
            print("ERROR: --batch requires --file <path>")
            sys.exit(1)
        batch_mode(args.file)
    else:
        interactive_mode()

if __name__ == "__main__":
    main()
