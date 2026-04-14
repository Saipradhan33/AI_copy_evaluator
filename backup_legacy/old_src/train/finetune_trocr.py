"""
finetune_trocr.py
-----------------
Fine-tunes microsoft/trocr-base-handwritten on your own labeled line crops.

Prerequisites:
  1. Run  src/data_prep/segment_lines.py   → generates dataset/line_crops/ + labels.csv
  2. Fill the 'text' column in dataset/labels.csv for every crop you want to use
     (label at least 200 rows; 400+ is better)

Output:
  models/trocr-finetuned/   — the saved model + processor

Run from the project root:
    python src/train/finetune_trocr.py

Training will take 2–5 hours on CPU for 300 samples.
Run overnight. The final model replaces EasyOCR for inference.
"""

import os
import sys
import csv
import evaluate                     # HuggingFace evaluate library
import torch
import numpy as np
from pathlib import Path
from PIL import Image
from torch.utils.data import Dataset, random_split
from transformers import (
    TrOCRProcessor,
    VisionEncoderDecoderModel,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    default_data_collator,
)

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parents[2]
DATASET_DIR = ROOT / "dataset"
LABELS_CSV  = DATASET_DIR / "labels.csv"
MODEL_OUT   = ROOT / "models" / "trocr-finetuned"

BASE_MODEL  = "microsoft/trocr-base-handwritten"   # ~334MB, manageable on CPU

# ── Hyper-parameters ─────────────────────────────────────────────────────────
EPOCHS      = 20
BATCH_SIZE  = 2       # keep small for CPU; increase to 8 if you have a GPU
LR          = 5e-5
MAX_LEN     = 128     # max output token length
VAL_SPLIT   = 0.1    # 10% of data used for validation
# ─────────────────────────────────────────────────────────────────────────────


class HandwritingDataset(Dataset):
    """Dataset of (line-crop PIL image, label string) pairs."""

    def __init__(self, rows, processor):
        self.rows      = rows
        self.processor = processor

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        img_path, label = self.rows[idx]

        image = Image.open(img_path).convert("RGB")

        # Encode image
        pixel_values = self.processor(
            images=image, return_tensors="pt"
        ).pixel_values.squeeze(0)

        # Encode label text to token ids
        with self.processor.as_target_processor():
            labels = self.processor(
                text=label, return_tensors="pt",
                padding="max_length", max_length=MAX_LEN, truncation=True
            ).input_ids.squeeze(0)

        # Replace pad tokens with -100 so they are ignored in the loss
        labels[labels == self.processor.tokenizer.pad_token_id] = -100

        return {"pixel_values": pixel_values, "labels": labels}


def load_labeled_rows():
    """Read labels.csv and return only fully-labeled rows."""
    rows = []
    skipped = 0
    with open(LABELS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            text = row["text"].strip()
            path = DATASET_DIR / row["image_path"]
            if text and path.exists():
                rows.append((str(path), text))
            else:
                skipped += 1
    print(f"Loaded {len(rows)} labeled samples ({skipped} skipped — unlabeled or missing).")
    return rows


def compute_metrics(processor, cer_metric):
    """Returns a metrics function for the Trainer."""
    def _compute(pred):
        label_ids = pred.label_ids
        pred_ids  = pred.predictions

        # Replace -100 back to pad id before decoding
        label_ids[label_ids == -100] = processor.tokenizer.pad_token_id

        pred_str  = processor.batch_decode(pred_ids,  skip_special_tokens=True)
        label_str = processor.batch_decode(label_ids, skip_special_tokens=True)

        cer = cer_metric.compute(predictions=pred_str, references=label_str)
        return {"cer": cer}

    return _compute


def main():
    if not LABELS_CSV.exists():
        print("ERROR: dataset/labels.csv not found.")
        print("Run  python src/data_prep/segment_lines.py  first.")
        sys.exit(1)

    rows = load_labeled_rows()
    if len(rows) < 10:
        print(f"ERROR: Only {len(rows)} labeled rows found. Label at least 10 (ideally 200+).")
        sys.exit(1)

    print(f"\nLoading base model: {BASE_MODEL} …")
    processor = TrOCRProcessor.from_pretrained(BASE_MODEL)
    model     = VisionEncoderDecoderModel.from_pretrained(BASE_MODEL)

    # Required decoder config for generation
    model.config.decoder_start_token_id = processor.tokenizer.cls_token_id
    model.config.pad_token_id           = processor.tokenizer.pad_token_id
    model.config.vocab_size             = model.config.decoder.vocab_size
    model.config.eos_token_id           = processor.tokenizer.sep_token_id
    model.config.max_length             = MAX_LEN
    model.config.early_stopping         = True
    model.config.no_repeat_ngram_size   = 3
    model.config.length_penalty         = 2.0
    model.config.num_beams              = 4

    # Train / val split
    dataset    = HandwritingDataset(rows, processor)
    val_size   = max(1, int(len(rows) * VAL_SPLIT))
    train_size = len(rows) - val_size
    train_ds, val_ds = random_split(dataset, [train_size, val_size])
    print(f"  Train: {train_size}  |  Val: {val_size}")

    cer_metric = evaluate.load("cer")

    training_args = Seq2SeqTrainingArguments(
        output_dir             = str(MODEL_OUT / "checkpoints"),
        num_train_epochs       = EPOCHS,
        per_device_train_batch_size = BATCH_SIZE,
        per_device_eval_batch_size  = BATCH_SIZE,
        predict_with_generate  = True,
        eval_strategy          = "epoch",
        save_strategy          = "epoch",
        logging_steps          = 10,
        learning_rate          = LR,
        warmup_steps           = 50,
        load_best_model_at_end = True,
        metric_for_best_model  = "cer",
        greater_is_better      = False,
        fp16                   = False,    # set True if you have a CUDA GPU
        report_to              = "none",   # disable W&B / MLflow
    )

    trainer = Seq2SeqTrainer(
        model         = model,
        args          = training_args,
        train_dataset = train_ds,
        eval_dataset  = val_ds,
        data_collator = default_data_collator,
        compute_metrics = compute_metrics(processor, cer_metric),
    )

    print("\nStarting fine-tuning …")
    trainer.train()

    # Save the final model + processor
    MODEL_OUT.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(MODEL_OUT))
    processor.save_pretrained(str(MODEL_OUT))
    print(f"\nFine-tuned model saved to {MODEL_OUT}")
    print("Run main.py to evaluate using your custom OCR model.")


if __name__ == "__main__":
    main()
