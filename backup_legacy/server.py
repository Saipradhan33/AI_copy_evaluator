from flask import Flask, request, jsonify
from flask_cors import CORS
import os, base64, requests
from rapidfuzz import fuzz
from answer_key import answer_keys

app = Flask(__name__)
CORS(app)

BIT_MAP = {"a":0,"b":1,"c":2}

def extract_text(img_path):
    with open(img_path,"rb") as f:
        image_b64 = base64.b64encode(f.read()).decode('utf-8')
    payload = {"model":"minicpm-v",
               "prompt":"Read the handwritten text. Output only what is written.",
               "images":[image_b64],"stream":False,
               "options":{"temperature":0.1,"num_predict":1024}}
    r = requests.post("http://localhost:11434/api/generate", json=payload, timeout=180)
    return r.json().get("response","").strip()

@app.route("/evaluate", methods=["POST"])
def evaluate():
    data       = request.json
    img_path   = data["path"]
    qbit       = data["qbit"]
    max_marks  = data.get("max_marks", 5)
    model_ans  = answer_keys[BIT_MAP[qbit]]
    extracted  = extract_text(img_path)
    score = fuzz.token_set_ratio(extracted.lower(), model_ans.lower())
    marks = round((score/100)*max_marks, 1)
    grade = "Excellent" if score>=80 else "Good" if score>=60 else "Average" if score>=40 else "Poor"
    return jsonify({"extracted":extracted,"model_answer":model_ans,
                    "similarity":score,"marks":marks,"grade":grade})

if __name__ == "__main__":
    app.run(port=5050)