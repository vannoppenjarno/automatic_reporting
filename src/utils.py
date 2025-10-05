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

# def find_similar_questions(question, top_k=5):
#     vector = embed_question(question).tolist()
#     results = collection.query(query_embeddings=[vector], n_results=top_k)
#     return results['documents'], results['metadatas']

# Potential Improvement: Use this clustering (to cluster similar questions) before prompting the LLM 
# from sklearn.cluster import KMeans
# def cluster_questions(logs, num_clusters=None):
#     """
#     Group similar questions using sentence embeddings + KMeans.
#     """
#     questions = [log["question"] for log in logs]

#     if len(questions) < 2:  # not enough to cluster
#         return {0: logs}

#     # Create embeddings
#     embeddings = embedder.encode(questions)

#     # Choose number of clusters (sqrt heuristic)
#     if num_clusters is None:
#         num_clusters = int(np.ceil(np.sqrt(len(questions))))

#     kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init="auto")
#     labels = kmeans.fit_predict(embeddings)

#     clustered = {}
#     for label, log in zip(labels, logs):
#         clustered.setdefault(label, []).append(log)

#     return clustered