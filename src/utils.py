from sentence_transformers import SentenceTransformer
import numpy as np
import hdbscan
import os

SENTENCE_EMBEDDING_MODEL = os.getenv("SENTENCE_EMBEDDING_MODEL")
EMBEDDER = SentenceTransformer(SENTENCE_EMBEDDING_MODEL)

def calculate_totals(reports):
    date = reports[0][1] if reports else ""
    total_question_count = sum(report[2] for report in reports)
    average_match = round(sum(report[3] for report in reports) / len(reports), 2) if reports else 0
    total_complete_misses = sum(report[4] for report in reports)
    overall_complete_misses_rate = round(total_complete_misses / total_question_count * 100, 2) if total_question_count > 0 else 0

    totals = {
        "date": date,
        "n_logs": total_question_count,
        "average_match": average_match,
        "complete_misses": total_complete_misses,
        "complete_misses_rate": overall_complete_misses_rate,
    }
    return totals

def embed(text):
    return EMBEDDER.encode(text, normalize_embeddings=True).tolist()  # returns list of vectors

def add_question_embeddings(data):
    """Embed all questions in the data dict in-place."""
    for log in data["logs"]:
        log["embedding"] = embed(log["question"])
    return data

def cluster_questions(data, min_cluster_size=2):
    """
    Cluster embeddings from the data dict using HDBSCAN.
    
    Args:
        data: dict containing 'logs', where each log has 'question' and 'embedding'.
        min_cluster_size: minimum cluster size for HDBSCAN.
    
    Returns:
        clusters: dict {cluster_label: list of question indices in data['logs']}
        noise: list of indices labeled as noise (-1)
    """
    logs = data.get("logs", [])
    if len(logs) < 2:
        return {0: list(range(len(logs)))}, []

    # Extract embeddings
    X = np.array([log["embedding"] for log in logs])

    # HDBSCAN clustering
    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size)
    labels = clusterer.fit_predict(X)

    clusters = {}
    noise = []
    for idx, label in enumerate(labels):
        if label == -1:
            noise.append(idx)
        else:
            clusters.setdefault(label, []).append(idx)

    return clusters, noise
    """
    Format clusters for LLM using data['logs'].
    
    
    """