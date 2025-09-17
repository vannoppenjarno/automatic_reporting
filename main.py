from read_emails import fetch_emails, parse_email
from prompt_LLM import generate_daily_report
from utils import save_report  

def main():
    emails = fetch_emails()

    if not emails:
        print("No new emails found.")
        return

    for date, email_list in emails.items():
        parsed = parse_email(date, email_list)

        # print("=" * 80)
        # print(f"Date: {parsed['date']}")
        # print(f"Number of Logs: {parsed['n_logs']}")
        # print(f"Average Match Score: {parsed['average_match']}")
        # print("=" * 80)

        # for i, qa in enumerate(parsed["logs"], 1):
        #     print(f"\nInteraction {i}:")
        #     print(f"Q: {qa['question']}")
        #     print(f"A: {qa['answer']}")
        #     print(f"Match: {qa['match_score']} | Time: {qa['time']}")

        # print("=" * 80)

        # Generate structured daily report with LLM
        report = generate_daily_report(parsed, model="mistral")
        # print("\n📊 Structured Daily Report:")
        # print(report)
        # print("=" * 80)

        # Save report to markdown file
        save_report(report, parsed["date"], folder="reports")


if __name__ == "__main__":
    main()