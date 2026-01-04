from get.models import get_embedding_function

def embed(text):
    embed_fn = get_embedding_function()
    return embed_fn.encode(text, normalize_embeddings=True).tolist()  # returns list of vectors

def add_question_embeddings(data):
    """Embed all questions in the data dict in-place."""
    for log in data["logs"]:
        log["embedding"] = embed(log["question"])
    return data
