import calendar, os, glob
from datetime import datetime
from datetime import timedelta
from dotenv import load_dotenv  # Import order important!

load_dotenv()  # Load environment variables from .env file

from src.fetch import fetch_emails, parse_email, parse_csv_logs
from src.prompt import create_prompt, generate_report, format_clusters_for_llm
from src.store import update_db_interactions, update_db_reports, fetch_questions, get_active_company_ids, get_active_talking_product_ids, get_ids
from src.utils import add_question_embeddings, cluster_questions

def main_daily(talking_product_id):
    emails = fetch_emails()  # TODO has to change in the future based in the company_id and talking_product_id
    if not emails:
        print("No new emails found.")
        return

    for date, email_list in emails.items():
        data = parse_email(date, email_list)
        data = add_question_embeddings(data)  # Embed questions in the data
        update_db_interactions(data, talking_product_id)  # Store interactions in both the relational and vector DB

        clusters, noise = cluster_questions(data)  # Cluster questions based on embeddings
        logs_text = format_clusters_for_llm(data, clusters, noise)
        print(logs_text)  # For debugging

        # Generate structured daily report with LLM
        prompt = create_prompt(logs_text)
        report = generate_report(prompt)
        update_db_reports(data, report, talking_product_id=talking_product_id)  # Save interactions + report in the SQLite database

def main_aggregate(date_range, report_type):
    # Fetch questions for the given date range
    data = fetch_questions(date_range)

    if not data:
        print(f"No questions found for date range {date_range}.")
        return

    clusters, noise = cluster_questions(data)
    logs_text = format_clusters_for_llm(data, clusters, noise)
    prompt = create_prompt(logs_text, title=f"{report_type} Interaction Report")
    report = generate_report(prompt)
    update_db_reports(data, report, report_type=report_type)

def main_csv(csv_file, company_id, talking_product_id):
    data = parse_csv_logs(csv_file)
    data = add_question_embeddings(data)
    update_db_interactions(data, talking_product_id)

    clusters, noise = cluster_questions(data)
    logs_text = format_clusters_for_llm(data, clusters, noise)
    print(logs_text)  # For debugging

    prompt = create_prompt(logs_text)
    report = generate_report(prompt)
    update_db_reports(data, report, report_type="aggregated", company_id=company_id, talking_product_id=talking_product_id)



if __name__ == "__main__":

    # Process daily reports for all active talking products
    active_company_ids = get_active_company_ids()
    for company_id in active_company_ids:
        active_talking_product_ids = get_active_talking_product_ids(company_id)
        for talking_product_id in active_talking_product_ids:
            main_daily(talking_product_id)

    # Process CSV logs for all files in the CSV_LOGS_DIR
    try:
        csv_dir = os.getenv("CSV_LOGS_DIR")  
        csv_files = glob.glob(os.path.join(csv_dir, "*.csv"))
        for csv_file in csv_files:
            talking_product_name = os.path.splitext(os.path.basename(csv_file))[0]
            talking_product_id, company_id = get_ids(talking_product_name)
            main_csv(csv_file, company_id, talking_product_id)
            os.remove(csv_file)  # delete after processing
    except Exception as e:
        print(f"Processing failed for {csv_file}: {e}")

    # Weekly and Monthly aggregation
    today = datetime.today()
    if today.weekday() == 6:  # If today is Sunday (Monday=0, Sunday=6)
        one_week_ago = today.date() - timedelta(days=6)
        date_range = (one_week_ago, today.date())
        main_aggregate(date_range, report_type="Weekly")

    last_day = calendar.monthrange(today.year, today.month)[1]  # Get the last day of the current month
    if today.day == last_day:  # If today is the end of the month
        first_day_this_month = today.replace(day=1)
        date_range = (first_day_this_month.date(), today.date())
        main_aggregate(date_range, report_type="Monthly")

    # Manual aggregation 
    # main_aggregate(date_range, report_type="Aggregated")