from supabase import create_client
from dotenv import load_dotenv
import os, chromadb, time


load_dotenv()  # Load environment variables from .env file


# ########## Configuration Settings ##########
CONTEXT_WINDOW = 1000000
MIN_TOKENS_PER_CLUSTER = 200
SCORE_IMPORTANCE = 0.5
LANG_CONFIDENCE_THRESHOLD = 0.5  # Minimum confidence for language detection
RETRIEVAL_K = 10  # Number of documents to retrieve for RAG


# ---------- Chunking ----------
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


# ---------- Namings ----------
SUBJECT_PATTERN = "jarno"
SENDER_PATTERN = "mail@i.no-reply-messages.com"


# ---------- Models ----------
LLM_MODEL = "models/gemini-2.5-flash"
EMBED_MODEL = "BAAI/bge-m3"
TOKEN_ENCODING_MODEL = "cl100k_base"
LLM_API_KEY = os.getenv("LLM_API_KEY")


# ---------- File paths ----------
CSV_LOGS_DIR = "C:/Users/jarno/Desktop/Digiole/code/automatic_reporting/csv_logs"
DAILY_PROMPT_TEMPLATE_PATH = "prompt_input/prompt_template.md"
RAG_PROMPT_TEMPLATE_PATH = "prompt_input/rag_prompt.md"
REPORT_STRUCTURE_PATH = "prompt_input/report_structure.json"
CONTEXT_PATH = "prompt_input/context.md"


# ---------- Adding company info ----------
COMPANY_NAME = ""
TALKING_PRODUCTS = ""
TALKING_PRODUCT_ADMIN_URLS = ""
TALKING_PRODUCT_URLS = ""
TALKING_PRODUCT_QR_CODES = ""


# ---------- Manual Aggregation Settings ----------
MANUAL_AGGREGATION_ENABLED = "false"
MANUAL_AGGREGATION_DATE_RANGE = ""
MANUAL_AGGREGATION_COMPANY_NAME = ""


# ---------- Supabase Settings ----------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE = create_client(SUPABASE_URL, SUPABASE_KEY)
REPORT_TABLES = {
    "daily": "Daily",
    "weekly": "Weekly",
    "monthly": "Monthly",
    "aggregated": "aggregated",
}


# ---------- Chroma Cloud Settings ----------
CHROMA_DATABASE = 'Test'
CHROMA_COLLECTION_NAME = "digiole_automatic_reporting"
CHROMA_KEY = os.getenv("CHROMA_KEY")
CHROMA_TENANT = os.getenv("CHROMA_TENANT")

for attempt in range(3):
    try:
        client = chromadb.CloudClient(
        api_key=CHROMA_KEY,
        tenant=CHROMA_TENANT,
        database=CHROMA_DATABASE
        )
        COLLECTION = client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)
        break
    except Exception as e:
        print(f"Connection attempt {attempt+1} failed: {e}")
        time.sleep(3)
else:
    raise RuntimeError("Failed to connect to Chroma Cloud after 3 retries.")


GOOGLE_CLIENT_ID = "634726700514-e1mk0mlff6lacdrs6f7a6shvlj9th6d3.apps.googleusercontent.com"
