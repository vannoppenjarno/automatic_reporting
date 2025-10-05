from sklearn.cluster import KMeans
import numpy as np

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

def cluster_questions(questions, embeddings, num_clusters=None):
    """
    Cluster similar questions using embeddings.
    - num_clusters: optional, if None use sqrt heuristic
    """
    if len(questions) < 2:  # not enough to cluster
        return {0: list(range(len(questions)))}

    # Choose number of clusters (sqrt heuristic)
    if num_clusters is None:
        num_clusters = int(np.ceil(np.sqrt(len(questions))))

    kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init="auto")
    labels = kmeans.fit_predict(np.array(embeddings))

    clusters = {}
    for idx, label in enumerate(labels):
        clusters.setdefault(label, []).append(idx)

    return clusters