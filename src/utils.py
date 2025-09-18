import os

REPORTS_DIR = "reports"

def save_report(report_text, date, folder=REPORTS_DIR):
    """Save the daily report as a markdown file in the reports folder."""
    # Ensure reports folder exists
    os.makedirs(folder, exist_ok=True)

    # Normalize date string (e.g., '2025-09-16' → '2025-09-16.md')
    filename = f"{date}.md"

    # Full path
    filepath = os.path.join(folder, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"✅ Report saved: {filepath}")


# Potential Improvement: Use this clustering (to cluster similar questions) before prompting the LLM 
# from sentence_transformers import SentenceTransformer
# from sklearn.cluster import KMeans
# Load embeddings model
# embedder = SentenceTransformer("all-MiniLM-L6-v2")
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