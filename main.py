import os
import calendar
from datetime import datetime
from src.fetch import fetch_emails, parse_email
from src.prompt import create_daily_prompt, generate_report, create_weekly_prompt, create_monthly_prompt
from src.store import store_questions, fetch_embeddings_by_date, save_report, init_db, update_db, fetch_past_week_reports, fetch_past_month_reports
from src.utils import calculate_totals, cluster_questions, format_clusters_for_llm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Access necessary environment variables
DB_PATH = os.getenv("DB_PATH")

def main_daily():
    # Initialize DB (only first run)
    if not os.path.exists(DB_PATH):
        init_db()

    emails = fetch_emails()
    if not emails:
        print("No new emails found.")
        return

    for date, email_list in emails.items():
        data = parse_email(date, email_list)

        store_questions(data)  # Store questions in the vector database
        questions, embeddings, metadatas = fetch_embeddings_by_date(date)  # Fetch embeddings for clustering
        clusters, noise = cluster_questions(questions, embeddings)  # Cluster questions based on embeddings
        logs_text = format_clusters_for_llm(clusters, noise, questions, embeddings, metadatas)
        print(logs_text)  # For debugging

        # Generate structured daily report with LLM
        prompt = create_daily_prompt(logs_text, data)
        report = generate_report(prompt, data)

        save_report(report, data["date"])  # EXTRA Save markdown file for quick easy access
        update_db(data, report)  # Save interactions + report in the SQLite database

def main_weekly(date):
    # Fetch past week's reports
    past_week_daily_reports = fetch_past_week_reports(date)
    
    if not past_week_daily_reports:
        print("No reports found for the past week.")
        return

    # Create weekly summary prompt
    totals = calculate_totals(past_week_daily_reports)
    past_week_daily_reports = [{"date": report[1], "content": report[6]} for report in past_week_daily_reports]
    prompt = create_weekly_prompt(past_week_daily_reports, totals)

    # Generate weekly summary report
    weekly_report = generate_report(prompt, totals)

    # Save weekly report
    save_report(weekly_report, f"week_{date.isocalendar()[1]}")  # EXTRA
    update_db(totals, weekly_report, report_type="weekly_reports")

def main_monthly(date):
    # Fetch past month's reports
    past_month_weekly_reports = fetch_past_month_reports(date)

    if not past_month_weekly_reports:
        print("No reports found for the past month.")
        return

    # Create monthly summary prompt
    totals = calculate_totals(past_month_weekly_reports)
    past_month_weekly_reports = [{"date": report[1], "content": report[6]} for report in past_month_weekly_reports]
    prompt = create_monthly_prompt(past_month_weekly_reports, totals)

    # Generate monthly summary report
    monthly_report = generate_report(prompt, totals)

    # Save monthly report
    save_report(monthly_report, f"month_{date.month}_{date.year}")  # EXTRA
    update_db(totals, monthly_report, report_type="monthly_reports")



if __name__ == "__main__":
    main_daily()

    today = datetime.today()
    if today.weekday() == 6:  # If today is Sunday (Monday=0, Sunday=6)
        main_weekly(today.date())

    last_day = calendar.monthrange(today.year, today.month)[1]  # Get the last day of the current month
    if today.day == last_day:  # If today is the end of the month
        main_monthly(today.date())