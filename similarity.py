from sentence_transformers import SentenceTransformer, util

_model = SentenceTransformer("all-MiniLM-L6-v2")


def compute(text1: str, text2: str) -> float:
    embeddings = _model.encode([text1, text2], convert_to_tensor=True)
    return float(util.cos_sim(embeddings[0], embeddings[1]))
