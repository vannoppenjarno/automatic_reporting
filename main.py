import os
from src.read_emails import fetch_emails, parse_email
from src.prompt_LLM import generate_daily_report
from src.database import init_db, save_interactions
from src.utils import save_report  

def main():
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
        report = generate_daily_report(parsed, model="mistral")

        # Save interactions + report in the SQLite database
        save_interactions(parsed, report)

        # Save report to markdown file
        save_report(report, parsed["date"], folder="reports")


if __name__ == "__main__":
    main()