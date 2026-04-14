"""
segment_lines.py
----------------
Reads every image from dataset/, auto-rotates it, then detects individual
text lines using a horizontal projection profile (sum of dark pixels per row).

Outputs:
  dataset/line_crops/<image_stem>/<line_num>.png  — one PNG per detected line
  dataset/labels.csv                              — CSV with image_path,text
                                                    (text column left blank)

Run from the project root:
    python src/data_prep/segment_lines.py
"""

import os
import sys
import cv2
import numpy as np
import csv
from pathlib import Path

# Allow importing preprocess from src/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from preprocess import preprocess_image

DATASET_DIR  = Path(__file__).resolve().parents[2] / "dataset"
CROPS_DIR    = DATASET_DIR / "line_crops"
LABELS_CSV   = DATASET_DIR / "labels.csv"

# ── Tuning knobs ────────────────────────────────────────────────────────────
MIN_LINE_HEIGHT   = 20    # pixels — ignore very thin bands (noise)
MAX_LINE_HEIGHT   = 200   # pixels — ignore huge bands (whole-page blobs)
VALLEY_THRESHOLD  = 0.08  # fraction of max projection where a row is "empty"
PAD               = 4     # padding added above/below each crop
# ────────────────────────────────────────────────────────────────────────────


def binarize(img_bgr):
    """Convert to grayscale + Otsu threshold. Returns binary image (0/255)."""
    gray  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    blur  = cv2.GaussianBlur(gray, (5, 5), 0)
    _, bw = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return bw


def horizontal_projection(bw):
    """Sum dark (foreground) pixels across each row. Returns 1D array."""
    return bw.sum(axis=1).astype(np.float32)


def find_line_bounds(proj, threshold_frac=VALLEY_THRESHOLD):
    """
    Find (y_start, y_end) pairs for each text line using the projection profile.
    Rows with projection below `threshold_frac * max_proj` are treated as gaps.
    """
    max_val   = proj.max() if proj.max() > 0 else 1
    threshold = max_val * threshold_frac
    in_line   = False
    bounds    = []
    start     = 0

    for y, val in enumerate(proj):
        if not in_line and val > threshold:
            in_line = True
            start   = y
        elif in_line and val <= threshold:
            in_line = False
            h = y - start
            if MIN_LINE_HEIGHT <= h <= MAX_LINE_HEIGHT:
                bounds.append((max(0, start - PAD), y + PAD))

    # Handle line that runs to bottom of image
    if in_line:
        h = len(proj) - start
        if MIN_LINE_HEIGHT <= h <= MAX_LINE_HEIGHT:
            bounds.append((max(0, start - PAD), len(proj)))

    return bounds


def segment_image(image_path):
    """Return list of line-crop numpy arrays for one image."""
    img  = preprocess_image(str(image_path))
    bw   = binarize(img)
    proj = horizontal_projection(bw)
    bounds = find_line_bounds(proj)

    crops = []
    for y0, y1 in bounds:
        crop = img[y0:y1, :]
        crops.append(crop)
    return crops


def main():
    CROPS_DIR.mkdir(parents=True, exist_ok=True)

    image_exts = {".jpg", ".jpeg", ".png"}
    image_files = [
        f for f in DATASET_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in image_exts
    ]

    if not image_files:
        print(f"No images found in {DATASET_DIR}")
        return

    rows = []   # (crop_path, empty_text)

    for img_path in sorted(image_files):
        print(f"Segmenting {img_path.name} …", end=" ", flush=True)

        crops = segment_image(img_path)
        print(f"{len(crops)} lines detected")

        out_dir = CROPS_DIR / img_path.stem
        out_dir.mkdir(parents=True, exist_ok=True)

        for idx, crop in enumerate(crops):
            crop_path = out_dir / f"{idx:04d}.png"
            cv2.imwrite(str(crop_path), crop)
            rows.append((str(crop_path.relative_to(DATASET_DIR)), ""))

    # Write / append labels.csv
    existing = set()
    if LABELS_CSV.exists():
        with open(LABELS_CSV, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)   # skip header
            existing = {row[0] for row in reader if row}

    new_rows = [r for r in rows if r[0] not in existing]

    mode = "a" if LABELS_CSV.exists() else "w"
    with open(LABELS_CSV, mode, newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if mode == "w":
            writer.writerow(["image_path", "text"])
        writer.writerows(new_rows)

    print(f"\nDone. {len(rows)} crops saved under {CROPS_DIR}")
    print(f"Labels file: {LABELS_CSV}")
    print("-> Open labels.csv and fill in the 'text' column for each crop.")


if __name__ == "__main__":
    main()
