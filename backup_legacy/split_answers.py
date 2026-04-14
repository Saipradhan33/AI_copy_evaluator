import re

def split_answers(text):
    """
    Split OCR text into individual answers by detecting common answer labels.

    Handles:
      - a) b) c)   A) B) C)
      - a. b. c.   A. B. C.
      - 1) 2) 3)   1. 2. 3.
      - Q1. Q2.    Q.1 Q.2

    NOTE: This function is kept as a fallback. The primary answer extraction
    now happens in ocr.extract_text() which splits the image into strips
    before OCR, making regex splitting on a single OCR string unnecessary
    in most cases.
    """
    # Broader pattern covering letters, numbers, and Q-prefixed labels
    pattern = r'\(?(?:[a-cA-C]|[1-3]|[Qq]\.?\s*[1-3])\s*[.)]\s*'
    answers = re.split(pattern, text)

    answers = [a.strip() for a in answers if a.strip()]

    print("Detected answers (split_answers fallback):", len(answers))

    return answers