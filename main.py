from read_emails import fetch_emails, parse_email
from prompt_LLM import generate_daily_report

def main():
    emails = fetch_emails()

    if not emails:
        print("No new emails found.")
        return

    for idx, email in enumerate(emails, start=1):
        parsed = parse_email(email.html)

        print("=" * 80)
        print(f"EMAIL {idx} - {email.subject}")
        print(f"Date: {parsed['date']}")
        print("=" * 80)

        for i, qa in enumerate(parsed["logs"], 1):
            print(f"\nInteraction {i}:")
            print(f"Q: {qa['question']}")
            print(f"A: {qa['answer']}")
            print(f"Match: {qa['match_score']} | Time: {qa['time']}")

        print("=" * 80)

        # Generate structured daily report with LLM
        report = generate_daily_report(parsed, model="mistral")
        print("\n📊 Structured Daily Report:")
        print(report)
        print("=" * 80)

        # Mark as read after fetching
        # email.mark_as_read()


if __name__ == "__main__":
    main()