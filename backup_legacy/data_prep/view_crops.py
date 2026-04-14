"""
view_crops.py
-------------
Displays each line crop alongside its current label from labels.csv.
Use this before labeling to confirm the segmentation looks correct.

Controls:
  ANY KEY  → next crop
  Q / ESC  → quit

Run from the project root:
    python src/data_prep/view_crops.py
"""

import csv
import sys
import cv2
import numpy as np
from pathlib import Path

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"
LABELS_CSV  = DATASET_DIR / "labels.csv"


def main():
    if not LABELS_CSV.exists():
        print(f"labels.csv not found at {LABELS_CSV}")
        print("Run segment_lines.py first.")
        sys.exit(1)

    with open(LABELS_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("labels.csv is empty.")
        sys.exit(1)

    print(f"Reviewing {len(rows)} crops. Press any key to advance, Q/ESC to quit.\n")

    for i, row in enumerate(rows):
        crop_path = DATASET_DIR / row["image_path"]
        label     = row["text"] or "<unlabeled>"

        if not crop_path.exists():
            print(f"  [{i+1}/{len(rows)}] Missing: {crop_path}")
            continue

        img = cv2.imread(str(crop_path))
        if img is None:
            print(f"  [{i+1}/{len(rows)}] Cannot read: {crop_path}")
            continue

        # Resize height to 80px for display, keep aspect ratio
        h, w = img.shape[:2]
        new_h = 80
        new_w = max(1, int(w * new_h / h))
        display = cv2.resize(img, (new_w, new_h))

        # Add black label bar below
        bar_h   = 30
        bar     = np.zeros((bar_h, new_w, 3), dtype=np.uint8)
        cv2.putText(bar, label[:80], (4, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        combined = np.vstack([display, bar])
        cv2.imshow(f"[{i+1}/{len(rows)}]  {crop_path.name}", combined)

        key = cv2.waitKey(0) & 0xFF
        cv2.destroyAllWindows()
        if key in (ord('q'), ord('Q'), 27):   # Q or ESC
            print("Quit.")
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
