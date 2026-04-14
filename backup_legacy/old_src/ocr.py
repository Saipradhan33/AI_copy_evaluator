"""
ocr.py
------
Extracts text from an exam sheet image.

Strategy (in order of preference):
  1. If  models/trocr-finetuned/  exists → use the fine-tuned TrOCR model
     (YOUR custom OCR, trained on your students' handwriting)
  2. Otherwise → fall back to EasyOCR (generic but functional)

Entry point used by main.py:
    texts = extract_text(image_path, num_answers=3)
    # returns List[str] — one string per answer region
"""

import os
import cv2
import numpy as np
from pathlib import Path
from PIL import Image

from preprocess import preprocess_image

FINETUNED_MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "trocr-finetuned"

# ── Lazy-load whichever backend is available ─────────────────────────────────
_backend      = None   # "trocr" or "easyocr"
_trocr_proc   = None
_trocr_model  = None
_easyocr_reader = None


def _load_backend():
    global _backend, _trocr_proc, _trocr_model, _easyocr_reader

    if FINETUNED_MODEL_DIR.exists():
        print(f"[OCR] Loading custom fine-tuned TrOCR from {FINETUNED_MODEL_DIR} …")
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        _trocr_proc  = TrOCRProcessor.from_pretrained(str(FINETUNED_MODEL_DIR))
        _trocr_model = VisionEncoderDecoderModel.from_pretrained(str(FINETUNED_MODEL_DIR))
        _trocr_model.eval()
        _backend = "trocr"
        print("[OCR] Custom TrOCR loaded.")
    else:
        print("[OCR] Fine-tuned model not found — using EasyOCR (generic).")
        print("[OCR] Train your model: python src/train/finetune_trocr.py")
        import easyocr
        _easyocr_reader = easyocr.Reader(['en'], gpu=False)
        _backend = "easyocr"


# ── Answer-region detection ──────────────────────────────────────────────────

def _detect_answer_regions(img, num_answers):
    """
    Detect answer region boundaries.
    First tries to find horizontal ruled divider lines on the exam sheet.
    Falls back to equal horizontal strips if no clear lines are found.
    Returns list of (y_start, y_end) tuples.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    kernel  = cv2.getStructuringElement(cv2.MORPH_RECT, (w // 3, 1))
    eroded  = cv2.erode(gray, kernel)
    dilated = cv2.dilate(eroded, kernel)

    _, thresh = cv2.threshold(dilated, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    divider_ys = []
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        if cw > w * 0.5 and ch < h * 0.03:
            divider_ys.append(y + ch // 2)

    divider_ys = sorted(set(divider_ys))

    if len(divider_ys) >= num_answers - 1:
        divider_ys = divider_ys[:num_answers - 1]
        boundaries = [0] + divider_ys + [h]
        regions = [(boundaries[i], boundaries[i + 1]) for i in range(num_answers)]
        print(f"  [OCR] Divider lines found at y={divider_ys}")
    else:
        regions = [
            (int(h * i / num_answers), int(h * (i + 1) / num_answers))
            for i in range(num_answers)
        ]
        print(f"  [OCR] No dividers found — using equal strips")

    return regions


# ── Per-strip OCR ─────────────────────────────────────────────────────────────

def _ocr_strip_trocr(strip_bgr):
    """Run fine-tuned TrOCR on a single image strip."""
    import torch
    pil = Image.fromarray(cv2.cvtColor(strip_bgr, cv2.COLOR_BGR2RGB))
    pixel_values = _trocr_proc(images=pil, return_tensors="pt").pixel_values
    with torch.no_grad():
        ids = _trocr_model.generate(pixel_values, max_new_tokens=300)
    return _trocr_proc.batch_decode(ids, skip_special_tokens=True)[0].strip()


def _ocr_strip_easyocr(strip_bgr):
    """Run EasyOCR on a single image strip."""
    results = _easyocr_reader.readtext(strip_bgr, detail=0, paragraph=True)
    return " ".join(results).strip()


# ── Public API ────────────────────────────────────────────────────────────────

def extract_text(image_path, num_answers=3):
    """
    Main entry point called by main.py.

    Returns a list of `num_answers` strings (one per answer region).

    Pipeline:
      1. Auto-rotate + crop  (preprocess.py)
      2. Detect answer region boundaries
      3. OCR each region with the best available model
    """
    global _backend
    if _backend is None:
        _load_backend()

    img     = preprocess_image(image_path)
    regions = _detect_answer_regions(img, num_answers)

    texts = []
    for i, (y0, y1) in enumerate(regions):
        strip = img[y0:y1, :]

        if _backend == "trocr":
            text = _ocr_strip_trocr(strip)
        else:
            text = _ocr_strip_easyocr(strip)

        preview = text[:80] + ("…" if len(text) > 80 else "")
        print(f"  [OCR strip {i+1}/{num_answers} | {_backend}] {preview}")
        texts.append(text)

    return texts