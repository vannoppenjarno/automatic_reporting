from sklearn.metrics.pairwise import euclidean_distances
from collections import Counter
import numpy as np
import hdbscan

def calculate_totals(reports):
    date = reports[0][1] if reports else ""
    total_interactions = sum(report[2] for report in reports)
    average_match = round(sum(report[3] for report in reports) / len(reports), 2) if reports else 0
    total_complete_misses = sum(report[4] for report in reports)
    overall_complete_misses_rate = round(total_complete_misses / total_interactions * 100, 2) if total_interactions > 0 else 0

    totals = {
        "date": date,
        "n_logs": total_interactions,
        "average_match": average_match,
        "complete_misses": total_complete_misses,
        "complete_misses_rate": overall_complete_misses_rate,
    }
    return totals

def cluster_questions_hdbscan(questions, embeddings, min_cluster_size=2):
    """
    Cluster embeddings with HDBSCAN and return cluster assignments.
    Returns:
      - clusters: dict {cluster_label: list of questions}
      - noise: list of indices labeled as noise (-1)
    """
    if len(questions) < 2:
        return {0: list(range(len(questions)))}, []

    X = np.array(embeddings)
    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size)
    labels = clusterer.fit_predict(X)

    clusters = {}
    noise = []
    for idx, label in enumerate(labels):
        if label == -1:
            noise.append(idx)
        else:
            clusters.setdefault(label, []).append(idx)

    # Map indices to actual question texts
    clusters = {
        cluster_id: [questions[i] for i in indices]
        for cluster_id, indices in clusters.items()
    }
    noise = [questions[i] for i in noise]

    return clusters, noise