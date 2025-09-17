from simplegmail import Gmail
from bs4 import BeautifulSoup


gmail = Gmail()


SUBJECT_PATTERN = "Jarno"
SENDER_PATTERN = "mail@i.no-reply-messages.com"

# Filter mails: Only process emails with subject or sender pattern matching Alfabia logs.
def filter_emails(email):
    subject = email.subject.lower()
    sender = email.sender.lower()
    return SUBJECT_PATTERN in subject or SENDER_PATTERN in sender

def fetch_emails():
    # Fetch unread inbox messages
    # emails = gmail.get_unread_inbox()
    raw_emails = gmail.get_messages()
    filtered_emails = [email for email in raw_emails if filter_emails(email)]

    return filtered_emails

def parse_email(email_html):
    soup = BeautifulSoup(email_html, "html.parser")

    # Header info
    date = soup.find("div", class_="date").get_text(strip=True)
    average_match = soup.find("span", string=lambda t: "Average Match:" in t).find_next().get_text(strip=True)

    logs = []
    qa_sections = soup.find_all("div", class_="qa-section")

    for qa in qa_sections:
        question = qa.find("h2").get_text(strip=True)
        answer = qa.find("p").get_text(strip=True)

        footer = qa.find("div", class_="qa-footer")
        match = footer.find("span", class_="match").get_text(strip=True).replace("Match:", "").strip()
        time = footer.find("span", class_="time").get_text(strip=True)

        logs.append({
            "question": question,
            "answer": answer,
            "match_score": match,
            "time": time
        })

    data = {
        "date": date,
        "average_match": average_match,
        "logs": logs
    }
    
    return data
