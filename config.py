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
CHROMA_COLLECTION_NAME = "interactions"
CHROMA_DATABASE = 'Test'


# ---------- Models ----------
LLM_MODEL = "models/gemini-2.5-flash"
EMBED_MODEL = "BAAI/bge-m3"
TOKEN_ENCODING_MODEL = "cl100k_base"


# ---------- File paths ----------
CSV_LOGS_DIR = "C:/Users/jarno/Desktop/Digiole/code/automatic_reporting/csv_logs"
DAILY_PROMPT_TEMPLATE_PATH = "prompt_input/prompt_template.md"
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