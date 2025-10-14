import ollama
import json
from json_repair import repair_json  # ensures valid JSON from LLM
import os

REPORT_STRUCTURE_PATH = os.getenv("REPORT_STRUCTURE_PATH")
CONTEXT_PATH = os.getenv("CONTEXT_PATH")
MODEL = os.getenv("MODEL")

def get_report_structure(title):
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
    with open(CONTEXT_PATH, 'r') as file:
        context = file.read()
    return context

def create_daily_prompt(logs_text, date):
    """
    Create a consistent prompt for generating a daily report from parsed email data.
    """
    title = f"Daily Interaction Report - {date}"
    report_structure = get_report_structure(title)
    context = get_context()

    # Consistent prompt
    prompt = f"""
    Generate a daily report in JSON format based on pre-clustered interaction logs.
    Important: Respond in valid JSON only (no extra text) and strictly follow the structure provided below.

    JSON template: {json.dumps(report_structure, indent=2)}

    Instructions for topics:
    - Generate a broad, descriptive topic label for each cluster, based on all questions in that cluster.
    - Include for each topic: observation, implication, strategic_alignment, recommendation, decision_required.
    - Include the pre-calculated representative_questions for each cluster (highest_frequency, closest_to_centroid).
    - Use the number of questions and the average match score in each cluster to determine and include question_count and average_match_score per topic.
    - Sort topics from most frequent to least frequent.

    Instructions for recommendations:
    - Suggest recommendations taking into account the following context {context}.
    - Try to have an alternative to the recommended action, considering cost efficiency, potential impact, and alignment with strategic objectives.
    - Recommendations should reflect insights from low scoring clusters, knowledge gaps, and frequency trends.
    - Include priority, action, optional alternative action, and expected impact for each recommendation.

    Instructions for executive_summary:
    - Summarize key objectives, status (On Track / At Risk / Off Track), and key decisions needed for management at a glance.

    Include an overall_takeaway summarizing the most important insights across all topics.

    Be sure to take into account the pre-clustering, the pre-calculated average match scores per cluster, the frequency of questions per cluster, and the given representative questions!
     
    Pre-clustered logs: {logs_text}

    Now generate the JSON output exactly as specified. Do not add extra text outside the JSON. keep it concise, avoid redundancy, and do not invent categories.
    """
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