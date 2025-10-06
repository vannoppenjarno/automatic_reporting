from sklearn.metrics.pairwise import euclidean_distances
from collections import Counter
import numpy as np
import hdbscan

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

def cluster_questions(questions, embeddings, min_cluster_size=2):
    """
    Cluster embeddings with HDBSCAN and return cluster assignments.
    Returns:
      - clusters: dict {cluster_label: list of question indices}
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

    return clusters, noise

def get_representative_questions(indices, questions, embeddings):
    """
    Return 1-2 representative questions for a single cluster:
      1️⃣ Highest frequency question
      2️⃣ Closest to centroid (if different)
    
    Args:
      indices: list of question indices in this cluster
      questions: list of all question texts
      embeddings: list of all embeddings
    
    Returns:
      list of representative questions (1 or 2 strings)
    """
    cluster_questions = [questions[i] for i in indices]
    cluster_embeddings = np.array([embeddings[i] for i in indices])

    # 1️⃣ Highest frequency question
    freq_question = Counter(cluster_questions).most_common(1)[0][0]

    # 2️⃣ Closest to centroid
    centroid = cluster_embeddings.mean(axis=0, keepdims=True)
    distances = euclidean_distances(cluster_embeddings, centroid)
    closest_idx = indices[np.argmin(distances)]
    centroid_question = questions[closest_idx]

    return [freq_question, centroid_question]

def format_clusters_for_llm(clusters, noise, questions, embeddings, metadatas):
    """
    Format clusters for LLM using questions and metadata.
    
    Args:
      clusters: dict {cluster_id: list of question indices}
      noise: list of question indices
      questions: list of question texts
      metadatas: list of dicts containing metadata (match_score, date, time, etc.)
    
    Returns:
      str: nicely formatted plain text
    """
    output_lines = []

    for cluster_id, indices in clusters.items():
        cluster_questions = [questions[i] for i in indices]
        cluster_scores = [metadatas[i].get("match_score", 0) for i in indices]
        avg_score = sum(cluster_scores) / len(cluster_scores) if cluster_scores else 0

        # Simple representative question: first question (can improve later)
        representative_questions = get_representative_questions(indices, questions, embeddings)

        output_lines.append(f"=== Cluster {cluster_id} ===")
        output_lines.append(f"Representative Questions: Highest frequency: {representative_questions[0]}, Closest to centroid: {representative_questions[1]}")
        output_lines.append(f"Average Match Score: {avg_score:.2f}%")
        output_lines.append("Questions:")
        for idx, q in enumerate(cluster_questions, 1):
            output_lines.append(f"{idx}. {q}")
        output_lines.append("")

    if noise:
        output_lines.append("=== Noise / Unclustered Questions ===")
        for i in noise:
            question = questions[i]
            score = metadatas[i].get("match_score", 0)
            output_lines.append(f"- {question} | Match Score: {score:.2f}%")
        output_lines.append("")

    return "\n".join(output_lines)