import os
import pandas as pd

from ocr import extract_text
from evaluate import evaluate_answer
from answer_key import answer_keys

dataset_path = "C:/Users/KIIT0001/Ai_copy_evaluator/dataset"

results = []

for file in os.listdir(dataset_path):

    if file.endswith((".jpg", ".png", ".jpeg")):

        path = os.path.join(dataset_path, file)
        print(f"\n===== Processing: {file} =====")

        # extract_text returns a list of strings — one per detected answer region.
        # num_answers is driven by how many answer keys we have (default 3).
        answers = extract_text(path, num_answers=len(answer_keys))

        print(f"  Regions extracted: {len(answers)}")

        for i in range(len(answer_keys)):

            if i < len(answers) and answers[i]:
                ans = answers[i]
            else:
                ans = "No answer detected"

            score = evaluate_answer(ans, answer_keys[i])

            results.append({
                "file": file,
                "question": i + 1,
                "answer": ans,
                "similarity": round(score, 4)
            })

            print(f"  Q{i+1} similarity: {score:.4f}")

df = pd.DataFrame(results)

os.makedirs("C:/Users/KIIT0001/Ai_copy_evaluator/output", exist_ok=True)

output_path = "C:/Users/KIIT0001/Ai_copy_evaluator/output/results.csv"
df.to_csv(output_path, index=False)

print(f"\nEvaluation complete. Results saved to {output_path}")