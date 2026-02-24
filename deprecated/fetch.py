from email.utils import parsedate_to_datetime
from collections import defaultdict
from bs4 import BeautifulSoup
from datetime import datetime
import base64
import os.path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from config import SUBJECT_PATTERN, SENDER_PATTERN, SCOPES, TOKEN_FILE, CREDENTIALS_FILE
from src.utils import detect_language


# ----------------------------
# AUTH: get Gmail API service
# ----------------------------
def get_gmail_service():
    """
    Returns an authenticated Gmail API service.
    First run: opens a browser → you log in once.
    Next runs: reuses and refreshes token.json automatically.
    """
    creds = None

    # Load existing token if present
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # If no valid credentials, either refresh or run browser flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Automatic refresh, no browser
            creds.refresh(Request())
        else:
            # First time: open browser, ask for consent
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save the new/updated token for next time
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    # Build Gmail API client
    service = build("gmail", "v1", credentials=creds)
    return service


# ----------------------------
# HELPERS to read Gmail emails
# ----------------------------
def _get_header(headers, name, default=""):
    """Find a header (Subject, From, Date, ...) in Gmail headers."""
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return default


def _gmail_message_to_dict(msg):
    """
    Convert a raw Gmail API message into a simple dict that behaves like
    your previous 'email' object.

    Returns:
        {
          "id": <gmail_message_id>,
          "subject": "...",
          "sender": "...",
          "date": "YYYY-MM-DD HH:MM:SS",
          "html": "<html>...</html>",
        }
    """
    headers = msg["payload"].get("headers", [])

    subject = _get_header(headers, "Subject", "")
    sender = _get_header(headers, "From", "")
    date_header = _get_header(headers, "Date", "")

    # Parse date header into a consistent string
    try:
        dt = parsedate_to_datetime(date_header)
        # Convert to local time and format
        dt = dt.astimezone()
        date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        # Fallback if parsing fails
        date_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    # Extract HTML body (if available)
    html = ""
    payload = msg["payload"]

    def decode_body(part):
        data = part.get("body", {}).get("data")
        if not data:
            return ""
        # Gmail body is base64url encoded
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    if payload.get("mimeType") == "text/html":
        html = decode_body(payload)
    else:
        # Walk through parts to find HTML
        parts = payload.get("parts", [])
        for part in parts:
            if part.get("mimeType") == "text/html":
                html = decode_body(part)
                break

    return {
        "id": msg["id"],
        "subject": subject,
        "sender": sender,
        "date": date_str,
        "html": html,
    }


def mark_as_read(service, message_id):
    """Remove the UNREAD label from a Gmail message."""
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"removeLabelIds": ["UNREAD"]},
    ).execute()


# ----------------------------
# YOUR existing logic, adapted
# ----------------------------
def filter_emails(email):
    """Filter emails based on subject and sender patterns."""
    # email is now a dict, not a simplegmail object
    subject = email["subject"].lower()
    sender = email["sender"].lower()
    return SUBJECT_PATTERN in subject and SENDER_PATTERN in sender


def sort_by_date(emails):
    """Sort and merge/group emails by date (YYYY-MM-DD)."""
    emails_per_date = defaultdict(list)
    for email in emails:
        date_key = email["date"].split(" ")[0]  # "YYYY-MM-DD"
        emails_per_date[date_key].append(email)
    return emails_per_date


def fetch_emails():
    service = get_gmail_service()

    response = service.users().messages().list(
        userId="me",
        labelIds=["INBOX", "UNREAD"],
        maxResults=500,
    ).execute()

    message_refs = response.get("messages", [])

    all_emails = []
    for ref in message_refs:
        msg = service.users().messages().get(
            userId="me",
            id=ref["id"],
            format="full",
        ).execute()

        email_dict = _gmail_message_to_dict(msg)

        if filter_emails(email_dict):
            all_emails.append(email_dict)

    sorted_emails = sort_by_date(all_emails)
    return sorted_emails, service


def parse_email(date, email_list, service):
    """
    Parse a list of emails for a specific date, extract Q&A logs and metrics,
    and store it in a data dictionary.
    """
    complete_misses = 0
    accumulated_match = 0
    logs = []

    for email in email_list:
        # Mark as read using Gmail API
        mark_as_read(service, email["id"])

        soup = BeautifulSoup(email["html"], "html.parser")
        qa_sections = soup.find_all("div", class_="qa-section")

        for qa in qa_sections:
            question = qa.find("h2").get_text(strip=True)
            answer = qa.find("p").get_text(strip=True)

            footer = qa.find("div", class_="qa-footer")
            match_text = (
                footer.find("span", class_="match")
                .get_text(strip=True)
                .replace("Match:", "")
                .strip()
            )
            time = footer.find("span", class_="time").get_text(strip=True)

            # Convert match_text to float
            match_score = float(match_text.replace("%", ""))

            if match_score == 0:
                complete_misses += 1

            accumulated_match += match_score
            logs.append(
                {
                    "question": question,
                    "answer": answer,
                    "match_score": match_score,
                    "date": date,
                    "time": time,
                    "language": detect_language(question),
                }
            )

    n_logs = len(logs)
    complete_misses_rate = round((complete_misses / n_logs) * 100, 2) if n_logs > 0 else 0
    average_match = round(float(accumulated_match) / n_logs, 2) if n_logs > 0 else 0

    data = {
        "date": date,
        "n_logs": n_logs,
        "average_match": average_match,
        "complete_misses": complete_misses,
        "complete_misses_rate": complete_misses_rate,
        "logs": logs,
    }

    return data

