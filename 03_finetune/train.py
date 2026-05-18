"""
Notebook 2 — Fine-Tuning with Unsloth + LoRA
Kaggle inputs required:
  - gemma-4-e2b-it  (Kaggle model: google/gemma-4/transformers/gemma-4-e2b-it/1)
  - gemma-triage-data  (dataset)
Output dataset: gemma-triage-outputs
  - merged_model/  (base + LoRA merged, includes tokenizer)
  - lora_adapter/
  - loss_curve.png
  - loss_log.csv
"""

# === CELL 1: Install Unsloth ===
# Run this cell first. Restart kernel after install before running Cell 2+.
# !pip install "unsloth[torch]>=2024.12" trl>=0.12 bitsandbytes matplotlib -q
# !pip install git+https://github.com/huggingface/transformers.git -q


# === CELL 2: Setup ===
import sys, json, pathlib, torch

DATA_DIR  = "/kaggle/input/datasets/codoes/gemma-triage-data"
MODEL_DIR = "/kaggle/input/models/google/gemma-4/transformers/gemma-4-e2b-it/1"

sys.path.append(DATA_DIR)
cfg = json.loads(pathlib.Path(f"{DATA_DIR}/pipeline_config.json").read_text())
cfg["training_data_path"] = f"{DATA_DIR}/training_dataset.json"
cfg["model_kaggle_path"]  = MODEL_DIR

torch.manual_seed(cfg["seed"])
print(f"Config loaded | seed={cfg['seed']} | lr={cfg['learning_rate']} | max_seq={cfg['max_seq_length']}")


# === CELL 3: Load model with FastLanguageModel ===
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=cfg["model_kaggle_path"],
    max_seq_length=cfg["max_seq_length"],
    load_in_4bit=False,   # E2B (2B params) fits in T4's 16 GB without quantization
    dtype=None,           # auto-detect — will use float16 on T4
)
tokenizer.model_max_length = cfg["max_seq_length"]
print(f"+ Model loaded | VRAM: {torch.cuda.memory_allocated()/1e9:.1f} GB used")


# === CELL 4: Apply LoRA ===
model = FastLanguageModel.get_peft_model(
    model,
    r=cfg["lora_rank"],
    lora_alpha=cfg["lora_alpha"],
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    random_state=cfg["seed"],
)
trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
total     = sum(p.numel() for p in model.parameters())
print(f"+ LoRA applied | trainable params: {trainable:,} / {total:,} "
      f"({100*trainable/total:.2f}%)")


# === CELL 5: Prepare dataset ===
from datasets import Dataset

# training_dataset.json is a JSON array — use json.loads, NOT line-by-line iteration
raw_lines = json.loads(open(cfg["training_data_path"]).read())

def format_example(example):
    """Merge system prompt into user turn; apply chat template to produce 'text' field."""
    msgs = example["messages"]
    if msgs[0]["role"] == "system":
        user_content      = msgs[0]["content"] + "\n\n" + msgs[1]["content"]
        assistant_content = msgs[2]["content"]
    else:
        user_content      = msgs[0]["content"]
        assistant_content = msgs[1]["content"]

    conversation = [
        {"role": "user",      "content": user_content},
        {"role": "assistant", "content": assistant_content},
    ]
    return {"text": tokenizer.apply_chat_template(
        conversation, tokenize=False, add_generation_prompt=False
    )}

dataset = Dataset.from_list(raw_lines)
dataset = dataset.map(format_example, remove_columns=dataset.column_names)
split   = dataset.train_test_split(
    test_size=cfg["val_split_fraction"], seed=cfg["seed"]
)
train_dataset = split["train"]
val_dataset   = split["test"]

print(f"+ Dataset prepared | train={len(train_dataset)} | val={len(val_dataset)}")
eff_batch = cfg["per_device_batch_size"] * cfg["grad_accum_steps"]
eff_steps = len(train_dataset) // eff_batch
print(f"  Effective batch={eff_batch} | steps/epoch~{eff_steps} | total~{eff_steps * cfg['epochs']}")


# === CELL 6: Configure trainer ===
from trl import SFTTrainer, SFTConfig
from transformers import EarlyStoppingCallback

training_args = SFTConfig(
    output_dir="/kaggle/working/checkpoints",
    num_train_epochs=cfg["epochs"],
    per_device_train_batch_size=cfg["per_device_batch_size"],
    per_device_eval_batch_size=cfg.get("per_device_eval_batch_size", 1),
    gradient_accumulation_steps=cfg["grad_accum_steps"],
    learning_rate=cfg["learning_rate"],
    warmup_ratio=cfg["warmup_ratio"],
    lr_scheduler_type="cosine",
    optim="adamw_8bit",
    fp16=True,
    max_seq_length=cfg["max_seq_length"],
    dataset_text_field="text",
    eval_strategy="steps",
    eval_steps=cfg["eval_steps"],
    save_strategy="steps",
    save_steps=cfg["eval_steps"],
    save_total_limit=3,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    seed=cfg["seed"],
    report_to="none",
)

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    args=training_args,
    callbacks=[EarlyStoppingCallback(
        early_stopping_patience=cfg["early_stopping_patience"]
    )],
)
print("+ Trainer configured")


# === CELL 7: Train ===
# Expected: initial loss ~2-4 (sequences now include full JSON responses).
# Loss should drop to ~0.5-1.5 by epoch 3. Early stopping patience=3.
print("Starting training...")
trainer.train()
print("+ Training complete")
print(f"  Best eval_loss: {trainer.state.best_metric:.4f}")


# === CELL 8: Save loss logs ===
import csv, matplotlib.pyplot as plt

log_history = trainer.state.log_history
train_steps = [(e["step"], e["loss"])      for e in log_history if "loss"      in e]
eval_steps  = [(e["step"], e["eval_loss"]) for e in log_history if "eval_loss" in e]

out = pathlib.Path("/kaggle/working")
with open(out / "loss_log.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["step", "train_loss", "eval_loss"])
    tmap = dict(train_steps); emap = dict(eval_steps)
    for s in sorted({s for s, _ in train_steps} | {s for s, _ in eval_steps}):
        w.writerow([s, tmap.get(s, ""), emap.get(s, "")])

fig, ax = plt.subplots(figsize=(10, 4))
if train_steps: ax.plot(*zip(*train_steps), label="train loss")
if eval_steps:  ax.plot(*zip(*eval_steps),  label="eval loss")
ax.set_xlabel("step"); ax.set_ylabel("loss"); ax.legend()
ax.set_title("Training Loss — Gemma 4 E2B LoRA Fine-tune")
fig.savefig(out / "loss_curve.png", dpi=120, bbox_inches="tight")
print("+ Loss logs saved")
