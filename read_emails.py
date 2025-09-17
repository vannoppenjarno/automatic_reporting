from simplegmail import Gmail
from bs4 import BeautifulSoup
from collections import defaultdict


gmail = Gmail()


SUBJECT_PATTERN = "jarno"
SENDER_PATTERN = "mail@i.no-reply-messages.com"

# Filter mails: Only process emails with subject or sender pattern matching Alfabia logs.
def filter_emails(email):
    subject = email.subject.lower()
    sender = email.sender.lower()
    return SUBJECT_PATTERN in subject and SENDER_PATTERN in sender

def sort_by_date(emails):
    # Sort and merge emails by date (YYYY-MM-DD)
    emails_per_date = defaultdict(list)
    for email in emails:
        emails_per_date[email.date.split(" ")[0]].append(email)
    return emails_per_date

def fetch_emails():
    # Fetch unread inbox messages
    # raw_emails = gmail.get_unread_inbox()
    raw_emails = gmail.get_messages()
    filtered_emails = [email for email in raw_emails if filter_emails(email)]
    sorted_emails = sort_by_date(filtered_emails)
    return sorted_emails

def parse_email(date, email_list):
    average_match = 0
    logs = []
    for email in email_list:
        email.mark_as_read()  # Mark as read after fetching
        soup = BeautifulSoup(email.html, "html.parser")        
        qa_sections = soup.find_all("div", class_="qa-section")
        for qa in qa_sections:
            question = qa.find("h2").get_text(strip=True)
            answer = qa.find("p").get_text(strip=True)

            footer = qa.find("div", class_="qa-footer")
            match = footer.find("span", class_="match").get_text(strip=True).replace("Match:", "").strip()
            time = footer.find("span", class_="time").get_text(strip=True)

            average_match += int(match[:-1])  # Remove % sign and convert to int
            logs.append({
                "question": question,
                "answer": answer,
                "match_score": match,
                "time": time
            })

    n_logs = len(logs)
    average_match = round(float(average_match) / n_logs, 2) if n_logs > 0 else 0
    data = {
        "date": date,
        "n_logs": n_logs,
        "average_match": average_match,
        "logs": logs
    }
    
    return data
