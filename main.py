import calendar, os, glob
from datetime import datetime
from datetime import timedelta
from src.fetch import fetch_emails, parse_email, parse_csv_logs
from src.embed import add_question_embeddings
from src.prompt import generate_report
from src.store import update_db_interactions, update_db_reports
from src.get.data import get_active_company_ids, get_active_talking_product_ids, get_latest_interaction_date, get_ids, get_company_id, fetch_questions
from src.utils import cluster_questions, format_clusters_for_llm

def main_daily(company_id, talking_product_id):
    emails = fetch_emails()  # TODO has to change in the future based in the company_id and talking_product_id
    if not emails:
        print("No new emails found.")
        return

    for date, email_list in emails.items():
        data = parse_email(date, email_list)
        data = add_question_embeddings(data)  # Embed questions in the data
        update_db_interactions(data, company_id, talking_product_id)  # Store interactions in both the relational and vector DB

        clusters, noise = cluster_questions(data)  # Cluster questions based on embeddings
        logs_text = format_clusters_for_llm(data, clusters, noise)
        print(logs_text)  # For debugging

        # Generate structured daily report with LLM
        report = generate_report(logs_text)
        update_db_reports(data, report, talking_product_id=talking_product_id)  # Save interactions + report in the SQLite database

def main_aggregate(date_range, report_type, talking_product_id=None, company_id=None):
    """Generate aggregated reports (Weekly, Monthly, or custom) for a given date range, talking product id and company id. The talking product id should correspond to the correct company id."""
    # Fetch questions for the given date range
    data = fetch_questions(date_range, talking_product_id=talking_product_id, company_id=company_id)

    if not data or data["n_logs"] == 0:
        print(f"No questions found for date range {date_range}.")
        return

    clusters, noise = cluster_questions(data)
    logs_text = format_clusters_for_llm(data, clusters, noise)
    report = generate_report(logs_text)
    update_db_reports(data, report, report_type, company_id, talking_product_id, date_range)

def main_csv(csv_file, company_id, talking_product_id):
    latest_date = get_latest_interaction_date(talking_product_id)  # Fetch latest processed date for this TP
    data = parse_csv_logs(csv_file, min_date_exclusive=latest_date)

    # If no new logs, just return (CSV was already fully processed)
    if data["n_logs"] == 0:
        print(f"No new data to process for talking_product_id={talking_product_id} from CSV {csv_file}.")
        return
    
    data = add_question_embeddings(data)
    update_db_interactions(data, company_id, talking_product_id)

    clusters, noise = cluster_questions(data)
    logs_text = format_clusters_for_llm(data, clusters, noise)
    print(logs_text)  # For debugging

    report = generate_report(logs_text)
    update_db_reports(data, report, report_type="aggregated", company_id=company_id, talking_product_id=talking_product_id)



if __name__ == "__main__":
    today = datetime.today()

    # 1. Process daily reports for all active talking products
    active_company_ids = get_active_company_ids()
    for company_id in active_company_ids:
        active_talking_product_ids = get_active_talking_product_ids(company_id)
        for talking_product_id in active_talking_product_ids:
            main_daily(company_id, talking_product_id)

            # 1.1. Weekly aggregation
            if today.weekday() == 6:  # If today is Sunday (Monday=0, Sunday=6)
                one_week_ago = today.date() - timedelta(days=6)
                date_range = (one_week_ago, today.date())
                main_aggregate(date_range, report_type="Weekly", talking_product_id=talking_product_id)

            # 1.2. Monthly aggregation
            last_day = calendar.monthrange(today.year, today.month)[1]  # Get the last day of the current month
            if today.day == last_day:  # If today is the end of the month
                first_day_this_month = today.replace(day=1)
                date_range = (first_day_this_month.date(), today.date())
                main_aggregate(date_range, report_type="Monthly", talking_product_id=talking_product_id)

    # 2. Process CSV logs for all files in the CSV_LOGS_DIR
    try:
        from config import CSV_LOGS_DIR
        csv_files = glob.glob(os.path.join(CSV_LOGS_DIR, "*.csv"))
        for csv_file in csv_files:
            talking_product_name = os.path.splitext(os.path.basename(csv_file))[0]  # CSV file name must be equal to the corresponding talking product name!
            talking_product_id, company_id = get_ids(talking_product_name)
            main_csv(csv_file, company_id, talking_product_id)
            os.remove(csv_file)  # delete after processing
    except Exception as e:
        print(f"Processing failed for {csv_file}: {e}")

    # 2.1. Manual aggregation
    from config import MANUAL_AGGREGATION_ENABLED, MANUAL_AGGREGATION_DATE_RANGE, MANUAL_AGGREGATION_COMPANY_NAME
    if MANUAL_AGGREGATION_ENABLED:
        company_id = get_company_id(MANUAL_AGGREGATION_COMPANY_NAME)
        main_aggregate(MANUAL_AGGREGATION_DATE_RANGE, report_type="aggregated", company_id=company_id)