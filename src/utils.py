import numpy as np
import hdbscan
import tiktoken
from collections import Counter
from sklearn.metrics.pairwise import euclidean_distances

from config import TOKEN_ENCODING_MODEL, CONTEXT_WINDOW, MIN_TOKENS_PER_CLUSTER
from .get.templates import get_daily_prompt_template, get_context

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

def count_tokens(text: str, model: str = TOKEN_ENCODING_MODEL) -> int:
    """
    Count the number of tokens in a given text using the specified model tokenizer.
    """
    encoding = tiktoken.get_encoding(model)
    return len(encoding.encode(text))

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

    # Normalize for comparison
    q1 = freq_question.strip().lower()
    q2 = centroid_question.strip().lower()

    if q1 == q2:
        return [freq_question]
    else:
        return [freq_question, centroid_question]

def format_clusters_for_llm(data, clusters, noise, max_tokens=CONTEXT_WINDOW, min_tokens_per_cluster=MIN_TOKENS_PER_CLUSTER):
    """
    Dynamically format clustered logs for LLM input, scaling number of questions
    per cluster by relative importance and using the full token budget.
    Includes token counting for prompt template, context, and cluster text.

    Args:
        data: dict containing 'logs', where each log has 'question', 'embedding', and metadata (match_score, date, time, etc.)
        clusters: dict {cluster_id: list of question indices in data['logs']}
        noise: list of question indices labeled as noise (-1)
        max_tokens: int, maximum allowed tokens for the prompt
    
    Returns:
        str: nicely formatted plain text for LLM prompt
    """
    logs = data.get("logs", [])
    questions = [log["question"] for log in logs]
    embeddings = [log["embedding"] for log in logs]
    scores = [log["match_score"] for log in logs]

    # --- Load static prompt info ---
    context = get_context()
    template_str = get_daily_prompt_template()

    # --- Count static tokens ---
    context_tokens = count_tokens(context)
    prompt_tokens = count_tokens(template_str)
    static_tokens = context_tokens + prompt_tokens  # Track total tokens used

    # --- Reserve dynamic space for clusters ---
    available_tokens = max_tokens - static_tokens
    if available_tokens <= 0:
        raise ValueError("Static prompt exceeds max token limit")
    
    # --- Compute cluster importance ---
    cluster_info = []
    total_importance = 0
    for cid, indices in clusters.items():
        cluster_scores = [scores[i] for i in indices]
        avg_score = sum(cluster_scores) / len(cluster_scores)
        size = len(indices)
        importance = size * (1 - avg_score / 100)
        cluster_info.append((cid, importance, avg_score, size))
        total_importance += importance

    # --- Sort clusters from most to least important ---
    cluster_info.sort(key=lambda x: x[1], reverse=True)

    # --- Build output dynamically ---
    output_lines = []
    used_tokens = static_tokens
    for cid, importance, avg_score, size in cluster_info:

        # Relative token budget for this cluster
        cluster_token_budget = max(min_tokens_per_cluster, int(available_tokens * (importance / total_importance)))

        # Representative questions 
        indices = clusters[cid]
        representatives = get_representative_questions(indices, questions, embeddings)
        cluster_text = f"Cluster {cid}\n"
        repr_text = [f"{i+1}. {q}" for i, q in enumerate(representatives)]
        cluster_text += "\n".join(repr_text) + "\n"

        # Sort by match_score ascending (to get most relevant questions)
        sorted_indices = sorted(indices, key=lambda i: scores[i])

        # Dynamically add as many questions as fit in the cluster_token_budget
        for idx, i in enumerate(sorted_indices):
            cluster_tokens = count_tokens(cluster_text)
            if questions[i] in representatives:
                continue  # Skip representative questions (deduplication)
            q_text = f"{idx + 1 + len(representatives)}. {questions[i]}"
            q_tokens = count_tokens(q_text)
            if cluster_tokens + q_tokens > cluster_token_budget:
                break
            cluster_text += q_text + "\n"
        
        # Check global budget
        if used_tokens + cluster_tokens > max_tokens:
            break

        output_lines.append(cluster_text)
        used_tokens += cluster_tokens

    # --- Fill any remaining tokens with noise sample ---
    remaining = max_tokens - used_tokens
    if noise and remaining > min_tokens_per_cluster:
        noise_text = "\nUnclustered Questions\n"
        noise_lines = []
        for count, i in enumerate(noise):
            line = f"{count + 1}. {questions[i]}"
            if count_tokens(noise_text + "\n".join(noise_lines) + line) > remaining:
                break
            noise_lines.append(line)
        noise_block = noise_text + "\n".join(noise_lines)
        output_lines.append(noise_block)
        used_tokens += count_tokens(noise_block)

    # --- Token Usage Diagnostics ---
    all_q_text = "\n".join(questions)
    all_q_tokens = count_tokens(all_q_text)
    print(f"\n🔹 Static tokens: {static_tokens}")
    print(f"🔹 Cluster tokens: {used_tokens - static_tokens}")
    print(f"🔸 All questions total tokens: {all_q_tokens}")
    print(f"🔸 % of all questions used: {(used_tokens - static_tokens) / all_q_tokens * 100:.1f}%")
    print(f"🔹 Total tokens: {used_tokens}/{max_tokens} ({used_tokens/max_tokens*100:.1f}% used)\n")
    if used_tokens < max_tokens * 0.98:
        print(f"⚠️ Token underuse: {max_tokens - used_tokens} tokens unused.")
    else:
        print("✅ Token utilization optimal.")

    return "\n".join(output_lines)

    """
    Format clusters for LLM using data['logs'].
    
    
    """