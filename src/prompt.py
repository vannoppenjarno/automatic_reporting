from json_repair import repair_json  # ensures valid JSON from LLM
from sklearn.metrics.pairwise import euclidean_distances
from collections import Counter
from string import Template
import numpy as np
import tiktoken
import ollama
import json
import os

REPORT_STRUCTURE_PATH = os.getenv("REPORT_STRUCTURE_PATH")
CONTEXT_PATH = os.getenv("CONTEXT_PATH")
DAILY_PROMPT_TEMPLATE_PATH = os.getenv("DAILY_PROMPT_TEMPLATE_PATH")
MODEL = os.getenv("MODEL")
CONTEXT_WINDOW = int(os.getenv("CONTEXT_WINDOW"))
TOKEN_ENCODING_MODEL = os.getenv("TOKEN_ENCODING_MODEL")

def get_report_structure(title="Automatic Interaction Report"):
    """
    Update the report structure template with new metadata values.
    """
    with open(REPORT_STRUCTURE_PATH, 'r') as file:
        report_structure = json.load(file)
    report_structure["title"] = title
    return report_structure

def get_context():
    """
    Load context from a markdown file.
    """
    with open(CONTEXT_PATH, 'r', encoding="utf-8") as file:
        context = file.read()
    return context

def get_daily_prompt_template():
    """
    Load the daily prompt template from a markdown file.
    """
    with open(DAILY_PROMPT_TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = Template(f.read())
    return template

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

    return [freq_question, centroid_question]

def format_clusters_for_llm(data, clusters, noise, max_tokens=CONTEXT_WINDOW):
    """
    Format clustered logs for the LLM prompt while respecting the token budget.
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

    # --- Load context + prompt and count base tokens ---
    report_structure = get_report_structure()
    context = get_context()
    template = get_daily_prompt_template()
    report_structure_tokens = count_tokens(json.dumps(report_structure, indent=2))
    context_tokens = count_tokens(context)
    prompt_tokens = count_tokens(template.template)

    # --- Compute cluster importance ---
    cluster_info = []
    for cid, indices in clusters.items():
        cluster_scores = [scores[i] for i in indices]
        avg_score = sum(cluster_scores) / len(cluster_scores)
        size = len(indices)
        importance = size * (1 - avg_score / 100)
        cluster_info.append((cid, importance, avg_score, size))

    # --- Sort clusters by importance (highest first) ---
    cluster_info.sort(key=lambda x: x[1], reverse=True)

    # --- Add clusters within token limit ---
    token_count = report_structure_tokens + context_tokens + prompt_tokens  # Track total tokens used
    output_lines = []
    for cid, _, avg_score, size in cluster_info:
        representative = get_representative_questions(clusters[cid], questions, embeddings)
        cluster_text = (
            f"=== Cluster {cid} ===\n"
            f"Representative Questions: {representative}\n"
        )
        tokens = count_tokens(cluster_text)
        if token_count + tokens > max_tokens:
            break
        token_count += tokens
        output_lines.append(cluster_text)

    # --- Add noise if space left ---
    if noise and token_count < max_tokens * 0.9:
        noise_text = "\n=== Noise / Unclustered Questions (sample) ===\n"
        sample_lines = [f"- {questions[i]} | Match: {scores[i]:.2f}%" for i in noise[:10]]
        noise_block = noise_text + "\n".join(sample_lines)
        noise_tokens = count_tokens(noise_block)
        if token_count + noise_tokens < max_tokens:
            token_count += noise_tokens
            output_lines.append(noise_block)

    return "\n".join(output_lines)

def create_daily_prompt(logs_text, date):
    """
    Create a consistent prompt for generating a daily report from parsed email data.
    """
    title = f"Daily Interaction Report - {date}"
    report_structure = get_report_structure(title)
    context = get_context()
    template = get_daily_prompt_template()
    
    prompt = template.substitute(
        json_template=json.dumps(report_structure, indent=2),
        context=context,
        logs_text=logs_text
    )
    return prompt

def add_calculations(json_report, data):
    json_report = json.loads(repair_json(json_report))  # Repair JSON if needed and convert str to dict
    json_report["overview"]["total_question_count"] = data['n_logs']
    json_report["overview"]["average_match_score"] = data['average_match']
    json_report["overview"]["complete_misses"] = data['complete_misses']
    json_report["overview"]["complete_misses_rate"] = data['complete_misses_rate']
    json_report = json.dumps(json_report, indent=2)  # Convert dict back to str
    return json_report
    
def generate_report(prompt, data, model=MODEL):
    """
    Generate a report based on a custom prompt using a local Ollama model.
    """

    # Call Ollama
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    raw_output = response["message"]["content"]
    output = add_calculations(raw_output, data)
    return output

def create_weekly_prompt(past_week_daily_reports, totals):
    """
    Create a consistent prompt for generating a weekly summary report from daily reports.
    """

    # Prepare daily reports as plain text
    reports_text = "\n\n".join(
        f"### Report for {report['date']}\n{report['content']}"
        for report in past_week_daily_reports
    )

    title = f"Weekly Interaction Report - Week of {totals['date']}"
    report_structure = get_report_structure(title)

    # Consistent prompt
    prompt = f"""
    Generate a weekly summary JSON report by aggregating daily JSON reports of the past week.
    Important: Respond in valid JSON only (no extra text) and follow the exact JSON format provided (don't invent sections). Here is the JSON template for the report structure: {json.dumps(report_structure, indent=2)}

    Base your analysis ONLY on the provided daily reports, and aggregate across them. Here are the daily reports:
    {reports_text}

    Now generate the JSON output exactly as specified. Do not add extra text outside JSON, keep it concise, avoid redundancy, do not invent categories, and do not repeat the same question / topics multiple times. Again, list most frequent topics to least frequent.
    """
    return prompt

def create_monthly_prompt(past_month_weekly_reports, totals):
    """
    Create a consistent prompt for generating a monthly summary report from weekly reports.
    """

    # Prepare weekly reports as plain text
    reports_text = "\n\n".join(
        f"### Report for Week {idx}\n{report['content']}"
        for idx, report in enumerate(past_month_weekly_reports, start=1)
    )

    title = f"Monthly Interaction Report - {totals['date']}"
    report_structure = get_report_structure(title)

    # Consistent prompt
    prompt = f"""
    Generate a monthly summary JSON report by aggregating weekly JSON reports of the past month.
    Important: Respond in valid JSON only (no extra text) and follow the exact JSON format provided (don't invent sections). Here is the JSON template for the report structure: {json.dumps(report_structure, indent=2)}

    Base your analysis ONLY on the provided weekly reports, and aggregate across them. Here are the weekly reports:
    {reports_text}

    Now generate the JSON output exactly as specified. Do not add extra text outside JSON, keep it concise, avoid redundancy, do not invent categories, and do not repeat the same question / topics multiple times. Again, list most frequent topics to least frequent.
    """
    return prompt