import ollama

def generate_daily_report(parsed_email, model="mistral"):
    """
    Generate a structured daily report from parsed logs using a local Ollama model.
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
    - Average Match Score: {parsed_email['average_match']}

    ## 2. Most Asked Topics & Common Questions
    - Group similar questions into clear topics.
    - Under each topic, show only **representative questions (Q)** and short summarized **answers (A)**.
    - Do not repeat the same question multiple times.
    - Keep it short and concise.

    ## 3. Language Trends
    - Detect and list which languages were used in the questions (approximate if needed).

    ## 4. Visitor Sentiment
    - Summarize sentiment (positive, neutral, negative).

    ## 5. Match Score Analysis
    - Identify lowest scoring topics (knowledge gaps).
    - Identify highest scoring topics (well covered).

    ## 6. Notable Insights / Patterns
    - Mention key trends, unusual questions, or repeated themes.
    - Suggest improvements to the knowledge base if needed.

    Here are the logs:
    {logs_text}

    Now generate the report exactly in this format. Keep it concise, avoid redundancy, and do not invent categories.
    """

    # prompt = f"""
    # You are tasked with generating a **structured daily report** from visitor interaction logs.
    # The report must always follow this exact format with the following sections:

    # # Daily Interaction Report ({parsed_email['date']})

    # ## 1. Overview
    # - Total Interactions: (count them)
    # - Estimated Average Match Score: (calculate an approximate trend: low, medium, high)

    # ## 2. Topics & Common Questions
    # - Group similar questions under clear topic headings.
    # - Provide representative questions and brief summarized answers.
    # - Mention average match scores for each topic.

    # ## 3. Match Score Analysis
    # - Identify lowest scoring topics (knowledge gaps).
    # - Identify highest scoring topics (well covered).

    # ## 4. Notable Insights
    # - Mention any trends, visitor interests, or unusual questions.
    # - Suggest knowledge base improvements if needed.

    # Here are the logs:
    # {logs_text}

    # Now generate the full structured report in the requested format.
    # """

    # Call Ollama
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )

    return response["message"]["content"]