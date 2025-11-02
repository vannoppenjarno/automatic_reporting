from collections import defaultdict
from simplegmail import Gmail
from bs4 import BeautifulSoup
from datetime import datetime
import os, csv

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
                "date": date,
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

def parse_csv_logs(csv_path):
    """
    Read Talking Product CSV logs and produce the same aggregated data structure
    as parse_email(), but allow multiple dates inside one CSV.
    """
    complete_misses = 0
    accumulated_match = 0
    logs = []

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(
            f,
            delimiter=",",
            quotechar='"',
            escapechar='\\',
            skipinitialspace=True
        )
        rows = list(reader)

    # Build structure grouped by date
    for row in rows:
        datetime_str = row["Date/Time"].strip()
        dt = datetime.strptime(datetime_str, "%d/%m/%Y, %H:%M:%S")

        date = dt.strftime("%Y-%m-%d")
        time = dt.strftime("%H:%M:%S")

        question = row["Statement"].strip()
        answer = row["Answer"].strip()
        raw_score = row["Score"].strip().replace("%", "")
        try:
            match_score = float(raw_score)
        except:
            print("SCORE PARSE ERROR:", raw_score, row)
            raise
        # match_score = float(raw_score) if raw_score else 0.0

        if match_score == 0:
            complete_misses += 1

        accumulated_match += match_score

        logs.append({
            "question": question,
            "answer": answer,
            "match_score": match_score,
            "date": date,
            "time": time
        })

    n_logs = len(logs)
    complete_misses_rate = round((complete_misses / n_logs) * 100, 2) if n_logs > 0 else 0
    average_match = round(accumulated_match / n_logs, 2) if n_logs > 0 else 0

    data = {
        "date": datetime.today().strftime("%Y-%m-%d"),  # Timestamp of CSV ingestion
        "n_logs": n_logs,
        "average_match": average_match,
        "complete_misses": complete_misses,
        "complete_misses_rate": complete_misses_rate,
        "logs": logs
    }

    return data