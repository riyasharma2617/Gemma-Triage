"""
Notebook 2 continuation — merge LoRA adapter into base weights and save.
Run these cells immediately after train.py cells in the same Kaggle session.
Cleans up checkpoints before committing to stay under 20 GB.
"""

# === CELL 9: Merge LoRA and save ===
import shutil, pathlib

out = pathlib.Path("/kaggle/working")

print("Saving raw LoRA adapter...")
model.save_pretrained(str(out / "lora_adapter"))
tokenizer.save_pretrained(str(out / "lora_adapter"))

print("Merging LoRA into base weights and saving (this takes ~2-3 min)...")
model.save_pretrained_merged(
    str(out / "merged_model"),
    tokenizer,
    safe_serialization=True,
)

# Verify tokenizer is included — NB3 loads tokenizer from merged_model/, not the hub
assert (out / "merged_model" / "tokenizer.json").exists(), (
    "Tokenizer not found in merged_model/ — save_pretrained_merged may have failed"
)
print("+ Tokenizer verified in merged_model/")


# === CELL 10: Disk cleanup (must run before committing output dataset) ===
shutil.rmtree(str(out / "checkpoints"), ignore_errors=True)

# Report disk usage
import subprocess
result = subprocess.run(
    ["du", "-sh", str(out)], capture_output=True, text=True
)
print(f"Working directory size after cleanup: {result.stdout.strip()}")
print("  merged_model/ ~4 GB + lora_adapter/ ~50 MB + logs should be well under 20 GB")


# === CELL 11: Final summary ===
files = list(out.rglob("*"))
print(f"\n+ Output dataset ready ({len(files)} files)")
for p in sorted(out.iterdir()):
    size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() \
           else p.stat().st_size
    print(f"  {p.name:<25} {size/1e6:>8.1f} MB")

print("\n-> Commit this notebook's output as Kaggle dataset: gemma-triage-outputs")
print("  Include: merged_model/, lora_adapter/, loss_curve.png, loss_log.csv")
print("  The next notebook (NB3) will attach gemma-triage-outputs as an input.")
