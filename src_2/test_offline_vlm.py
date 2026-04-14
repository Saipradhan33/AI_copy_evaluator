import os
import base64
import requests
from rapidfuzz import fuzz
from answer_key import answer_keys

# =========================
# ENCODE IMAGE - RAW, NO PREPROCESSING
# =========================
def encode_image(img_path):
    with open(img_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

# =========================
# EXTRACT TEXT VIA MINICPM-V
# =========================
def extract_text(img_path):
    image_b64 = encode_image(img_path)
    payload = {
        "model": "minicpm-v",
        "prompt": "Read the handwritten text in this image. Output only what is written. Do not add anything.",
        "images": [image_b64],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 1024}
    }
    response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=600)
    return response.json().get("response", "").strip()

# =========================
# EVALUATOR
# =========================
def evaluate_answer(extracted_text, model_answer, max_marks=5):
    score = fuzz.token_set_ratio(extracted_text.lower(), model_answer.lower())
    marks = round((score / 100) * max_marks, 1)
    if score >= 80:   grade = "Excellent"
    elif score >= 60: grade = "Good"
    elif score >= 40: grade = "Average"
    else:             grade = "Poor"
    return {"similarity": round(score, 2), "marks": marks, "max_marks": max_marks, "grade": grade}

# =========================
# PIPELINE
# =========================
def run_pipeline(img_path, question_bit, max_marks=5):
    print("=" * 60)
    print(f"Reading image: {os.path.basename(img_path)} | Question: {question_bit.upper()}")

    model_answer = answer_keys[{"a": 0, "b": 1, "c": 2}[question_bit]]

    try:
        extracted = extract_text(img_path)
        print(f"\n[EXTRACTED]\n{extracted}")
        print(f"\n[MODEL ANSWER]\n{model_answer}")

        ev = evaluate_answer(extracted, model_answer, max_marks)
        print(f"\n[EVALUATION]")
        print(f"  Similarity : {ev['similarity']}%")
        print(f"  Marks      : {ev['marks']} / {ev['max_marks']}")
        print(f"  Grade      : {ev['grade']}")
        print("=" * 60)
        return extracted

    except requests.exceptions.ConnectionError:
        print("ERROR: Core Engine is not running. Run system setup.")
        return ""
    except Exception as e:
        print(f"Error: {e}")
        return ""

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    test_cases = [
        {
            "path": "dataset_final/datasetA/1)a_0.jpg",
            "bit": "a",
            "max_marks": 5
        },
        {
            "path": "C:/Users/KIIT0001/Ai_copy_evaluator/dataset_final/datasetB/1)b_1.jpg",
            "bit": "b",
            "max_marks": 5
        },
        {
            "path": "C:/Users/KIIT0001/Desktop/Ai_copy_evaluator/dataset_final/datasetC/IMG_1C.jpg",
            "bit": "c",
            "max_marks": 5
        },
    ]

    for tc in test_cases:
        if os.path.exists(tc["path"]):
            run_pipeline(tc["path"], tc["bit"], tc["max_marks"])
        else:
            print(f"File not found: {tc['path']}")