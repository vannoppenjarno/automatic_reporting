from simplegmail import Gmail
from bs4 import BeautifulSoup
from collections import defaultdict
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Access variables
SUBJECT_PATTERN = os.getenv("SUBJECT_PATTERN")
SENDER_PATTERN = os.getenv("SENDER_PATTERN")

def filter_emails(email):
    """Filter emails based on subject and sender patterns."""
    subject = email.subject.lower()
    sender = email.sender.lower()
    return SUBJECT_PATTERN in subject and SENDER_PATTERN in sender

def sort_by_date(emails):
    """Sort and merge/group emails by date (YYYY-MM-DD)."""
    emails_per_date = defaultdict(list)
    for email in emails:
        emails_per_date[email.date.split(" ")[0]].append(email)
    return emails_per_date

def fetch_emails():
    """Fetch unread emails from Gmail matching specific patterns and group them by date."""
    gmail = Gmail()
    raw_emails = gmail.get_unread_inbox()  # Fetch unread inbox messages
    # raw_emails = gmail.get_messages()
    filtered_emails = [email for email in raw_emails if filter_emails(email)]
    sorted_emails = sort_by_date(filtered_emails)
    return sorted_emails

def parse_email(date, email_list):
    """Parse a list of emails for a specific date, extract Q&A logs and metrics, and store it in a data dictionary."""
    complete_misses = 0
    accumulated_match = 0
    logs = []
    for email in email_list:
        email.mark_as_read()  # Mark as read after fetching
        soup = BeautifulSoup(email.html, "html.parser")        
        qa_sections = soup.find_all("div", class_="qa-section")
        for qa in qa_sections:
            question = qa.find("h2").get_text(strip=True)
            answer = qa.find("p").get_text(strip=True)

            footer = qa.find("div", class_="qa-footer")
            match_text = footer.find("span", class_="match").get_text(strip=True).replace("Match:", "").strip()
            time = footer.find("span", class_="time").get_text(strip=True)

            # Convert match_text to float
            match_score = float(match_text.replace("%", ""))

            if match_score == 0:
                complete_misses += 1

            accumulated_match += match_score
            logs.append({
                "question": question,
                "answer": answer,
                "match_score": match_score,
                "time": time
            })

    n_logs = len(logs)
    complete_misses_rate = round((complete_misses / n_logs) * 100, 2) if n_logs > 0 else 0
    average_match = round(float(accumulated_match) / n_logs, 2) if n_logs > 0 else 0
    data = {
        "date": date,
        "n_logs": n_logs,
        "average_match": average_match,
        "complete_misses": complete_misses,
        "complete_misses_rate": complete_misses_rate,
        "logs": logs
    }
    
    return data
