import os
import calendar
from datetime import datetime
from src.fetch import fetch_emails, parse_email
from src.prompt import create_daily_prompt, generate_report, create_weekly_prompt, create_monthly_prompt
from src.store import save_report, init_db, update_db, fetch_past_week_reports, fetch_past_month_reports
from src.utils import calculate_totals

def main_daily():
    # Initialize DB (only first run)
    if not os.path.exists("insights.db"):
        init_db()

    emails = fetch_emails()
    if not emails:
        print("No new emails found.")
        return

    for date, email_list in emails.items():
        parsed = parse_email(date, email_list)

        # Generate structured daily report with LLM
        prompt = create_daily_prompt(parsed)
        report = generate_report(prompt, model="mistral")
 
        save_report(report, parsed["date"], folder="reports")  # EXTRA Save markdown file for quick easy access
        update_db(parsed, report)  # Save interactions + report in the SQLite database

def main_weekly(date):
    # Fetch past week's reports
    past_week_reports = fetch_past_week_reports(date)
    
    if not past_week_reports:
        print("No reports found for the past week.")
        return

    # Create weekly summary prompt
    totals = calculate_totals(past_week_reports)
    past_week_reports = [{"date": report[1], "content": report[6]} for report in past_week_reports]
    prompt = create_weekly_prompt(past_week_reports, totals)

    # Generate weekly summary report
    weekly_report = generate_report(prompt, model="mistral")

    # Save weekly report
    save_report(weekly_report, f"week_{date.isocalendar()[1]}", folder="reports")  # EXTRA
    update_db(totals, weekly_report, report_type="weekly_reports")

def main_monthly(date):
    # Fetch past month's reports
    monthly_reports = fetch_past_month_reports(date)

    if not monthly_reports:
        print("No reports found for the past month.")
        return

    # Create monthly summary prompt
    prompt = create_monthly_prompt([
        {"date": report[1], "content": report[6]} for report in monthly_reports
    ])

    # Generate monthly summary report
    monthly_report = generate_report(prompt, model="mistral")

    # EXTRA Save monthly report
    save_report(monthly_report, f"month_{date.month}_{date.year}", folder="reports")



if __name__ == "__main__":
    main_daily()

    today = datetime.today()
    if today.weekday() == 6:  # If today is Sunday (Monday=0, Sunday=6)
        main_weekly(today.date())

    last_day = calendar.monthrange(today.year, today.month)[1]  # Get the last day of the current month
    if today.day == last_day:  # If today is the end of the month
        main_monthly(today.date())