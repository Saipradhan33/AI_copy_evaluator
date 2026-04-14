from sentence_transformers import SentenceTransformer, util

# all-MiniLM-L6-v2 is ~90MB vs ~420MB for all-mpnet-base-v2.
# Quality is nearly identical for short answer similarity; much lower memory footprint.
model = SentenceTransformer('all-MiniLM-L6-v2')

def evaluate_answer(student_answer, answer_key):

    emb1 = model.encode(answer_key, convert_to_tensor=True)
    emb2 = model.encode(student_answer, convert_to_tensor=True)

    score = util.cos_sim(emb1, emb2)

    return score.item()