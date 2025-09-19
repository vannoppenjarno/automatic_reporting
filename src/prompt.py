import ollama

def create_daily_prompt(parsed_email):
    """
    Create a consistent prompt for generating a daily report from parsed email data.
    """

    # Prepare logs as plain text
    logs_text = "\n".join(
        f"Q: {log['question']}\nA: {log['answer']}\nMatch: {log['match_score']} | Time: {log['time']}\n"
        for log in parsed_email["logs"]
    )

    # Consistent prompt
    prompt = f"""
    You are tasked with generating a **short and structured daily report** from visitor interaction logs.
    The report must always follow this exact format with the following sections:

    # Daily Interaction Report ({parsed_email['date']})

    ## 1. Overview
    - Total Interactions: {len(parsed_email['logs'])}
    - Average Match Score: {parsed_email['average_match']}%
    - Number of complete misses: {parsed_email['complete_misses']}
    - Complete Misses Rate: {parsed_email['complete_misses_rate']}%
    - Language trends: Detect and list which languages were used in the questions (approximate if needed).
    - Visitor sentiment: Summarize overall sentiment (positive, neutral, negative).
    - Peak interaction times: Identify busiest times of the day (morning, afternoon, evening).

    ## 2. Most Asked Topics & Common Questions
    - Group similar questions into clear topics.
    - Under each topic, show only **representative questions (Q)** and short summarized **answers (A)**.
    - Do not repeat the same question multiple times.
    - Keep it short and concise.

    ## 3. Match Score Analysis
    - Identify lowest scoring topics (knowledge gaps).
    - Identify highest scoring topics (well covered).

    ## 4. Notable Insights / Patterns
    - Mention key trends, unusual questions, or repeated themes.
    - Suggest improvements to the knowledge base if needed.

    Here are the logs:
    {logs_text}

    Now generate the report exactly in this format. Keep it concise, avoid redundancy, and do not invent categories.
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

def create_weekly_prompt(past_week_reports, totals):
    """
    Create a consistent prompt for generating a weekly summary report from daily reports.
    """
    # AGGREGATE
    # Prepare daily reports as plain text
    reports_text = "\n\n".join(
        f"### Report for {report['date']}\n{report['content']}"
        for report in past_week_reports
    )

    # Consistent prompt
    prompt = f"""
    You are tasked with generating a **short and structured weekly summary report** from daily interaction reports.
    The weekly report must always follow this exact format with the following sections:

    # Weekly Summary Report ({totals['date']})

    ## 1. Weekly Overview
    - Total Interactions: {totals['n_logs']}
    - Average Match Score: {totals['average_match']}%
    - Total Complete Misses: {totals['complete_misses']}
    - Overall Complete Misses Rate: {totals['complete_misses_rate']}%
    - Language trends: Summarize which languages were most used throughout the week.
    - Visitor sentiment: Summarize overall sentiment trends (positive, neutral, negative).
    - Peak interaction times: Identify busiest times of the week (morning, afternoon, evening).

    ## 2. Key Topics & Common Questions
    - Identify recurring topics across the week.
    - Highlight any new topics that emerged during the week.
    - Under each topic, show only **representative questions (Q)** and short summarized **answers (A)**.
    - Do not repeat the same question multiple times.
    - Keep it short and concise.

    ## 3. Match Score Analysis
    - Identify lowest scoring topics (knowledge gaps) across the week.
    - Identify highest scoring topics (well covered) across the week.

    ## 4. Notable Insights / Patterns
    - Mention key trends, unusual questions, or repeated themes observed during the week.
    - Suggest improvements to the knowledge base if needed.

    Here are the daily reports:
    {reports_text}

    Now generate the weekly summary report exactly in this format. Keep it concise, avoid redundancy, and do not invent categories.
    """
    return prompt

def create_monthly_prompt(weekly_reports):
    """
    Create a consistent prompt for generating a monthly summary report from weekly reports.
    """

    # AGGREGATE
    # Prepare weekly reports as plain text
    reports_text = "\n\n".join(
        f"### Report for Week {report['week_number']} ({report['date_range']})\n{report['content']}"
        for report in weekly_reports
    )

    # Consistent prompt
    prompt = f"""
    You are tasked with generating a **short and structured monthly summary report** from weekly interaction reports.
    The monthly report must always follow this exact format with the following sections:

    # Monthly Summary Report

    ## 1. Monthly Overview
    - Total Interactions: Sum of total interactions from all weeks.
    - Average Match Score: Average of weekly average match scores.
    - Total Complete Misses: Sum of complete misses from all weeks.
    - Overall Complete Misses Rate: Overall rate calculated from total interactions and total complete misses.
    - Language trends: Summarize which languages were most used throughout the month.
    - Visitor sentiment: Summarize overall sentiment trends (positive, neutral, negative).
    - Peak interaction times: Identify busiest times of the month (morning, afternoon, evening).

    ## 2. Key Topics & Common Questions
    - Identify recurring topics across the month.
    - Highlight any new topics that emerged during the month.
    - Under each topic, show only **representative questions (Q)** and short summarized **answers (A)**.
    - Do not repeat the same question multiple times.
    - Keep it short and concise.

    ## 3. Match Score Analysis
    - Identify lowest scoring topics (knowledge gaps) across the month.
    - Identify highest scoring topics (well covered) across the month.

    ## 4. Notable Insights / Patterns
    - Mention key trends, unusual questions, or repeated themes observed during the month.
    - Suggest improvements to the knowledge base if needed.

    Here are the weekly reports:
    {reports_text}

    Now generate the monthly summary report exactly in this format. Keep it concise, avoid redundancy, and do not invent categories.
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