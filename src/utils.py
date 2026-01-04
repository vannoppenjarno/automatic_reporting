import numpy as np
import hdbscan

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