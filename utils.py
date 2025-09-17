import os

REPORTS_DIR = "reports"

def save_report(report_text, date, folder=REPORTS_DIR):
    """Save the daily report as a markdown file in the reports folder."""
    # Ensure reports folder exists
    os.makedirs(folder, exist_ok=True)

    # Normalize date string (e.g., '2025-09-16' → '2025-09-16.md')
    filename = f"{date}.md"

    # Full path
    filepath = os.path.join(folder, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"✅ Report saved: {filepath}")
