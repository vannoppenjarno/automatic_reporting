import ollama
import json

def get_report_structure(title, parsed_email):
    """
    Update the report structure template with new metadata values.
    """
    with open('report_structure.json', 'r') as file:
        report_structure = json.load(file)
    report_structure["title"] = title
    report_structure["overview"]["total_interactions"] = len(parsed_email['logs'])
    report_structure["overview"]["average_match_score"] = round(parsed_email['average_match'])
    report_structure["overview"]["complete_misses"] = parsed_email['complete_misses']
    report_structure["overview"]["complete_misses_rate"] = round(parsed_email['complete_misses_rate'])
    return report_structure

def get_context():
    """
    Load context from a markdown file.
    """
    with open('context.md', 'r') as file:
        context = file.read()
    return context

def create_daily_prompt(parsed_email):
    """
    Create a consistent prompt for generating a daily report from parsed email data.
    """

    # Prepare logs as plain text
    logs_text = "\n".join(
        f"Question: {log['question']} | Match: {log['match_score']} | Time: {log['time']}\n"
        for log in parsed_email["logs"]
    )

    title = f"Daily Interaction Report - {parsed_email['date']}"
    report_structure = get_report_structure(title, parsed_email)
    context = get_context()

    # Consistent prompt
    prompt = f"""
    Generate a daily report based on a structured JSON file and interaction logs.
    Important: Respond in valid JSON only (no extra text) and follow the exact JSON format provided (don't invent sections). Here is the JSON template for the report structure: {json.dumps(report_structure, indent=2)}

    Some additional instructions for the topics:
    - Group semantically similar questions under ONE topic.
    - Do not split by minor wording differences.
    - Use a broad, descriptive label for topics.
    - Always merge related sub-questions under one topic entry.
    - Provide only one representative_question per topic.
    - List topics from most frequent to least frequent.

    Some additional instructions for the recommended actions:
    - Suggest recommendations taking into account the following context {context}.
    - Suggest knowledge base entries that need updating or expanding based on lowest scoring topics (knowledge gaps) and their frequency.
    - Suggest example questions based on FAQ questions and the highest scoring topics that are already well covered.
    - Prioritize cheapest/easiest to implement and highest potential customer satisfaction.

    Here are the interaction logs:
    {logs_text}

    Now generate the JSON output exactly as specified. Do not add extra text outside JSON, keep it concise, avoid redundancy, and do not invent categories.
    """
    return prompt

def generate_report(prompt, model="mistral"):
    """
    Generate a report based on a custom prompt using a local Ollama model.
    """

    # Call Ollama
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )

    return response["message"]["content"]

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
    report_structure = get_report_structure(title, totals)

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
    report_structure = get_report_structure(title, totals)

    # Consistent prompt
    prompt = f"""
    Generate a monthly summary JSON report by aggregating weekly JSON reports of the past month.
    Important: Respond in valid JSON only (no extra text) and follow the exact JSON format provided (don't invent sections). Here is the JSON template for the report structure: {json.dumps(report_structure, indent=2)}

    Base your analysis ONLY on the provided weekly reports, and aggregate across them. Here are the weekly reports:
    {reports_text}

    Now generate the JSON output exactly as specified. Do not add extra text outside JSON, keep it concise, avoid redundancy, do not invent categories, and do not repeat the same question / topics multiple times. Again, list most frequent topics to least frequent.
    """
    return prompt

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