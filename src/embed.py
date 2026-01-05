from .get.models import get_embed_model
embed_model = get_embed_model()  # load once at import time

def embed_fn(text):
    return embed_model.encode(text, normalize_embeddings=True).tolist()  # returns list of vectors

def add_question_embeddings(data):
    """Embed all questions in the data dict in-place."""
    for log in data["logs"]:
        log["embedding"] = embed_fn(log["question"])
    return data
