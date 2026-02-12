import hashlib, os
from typing import Any, Dict, List
from json2markdown import convert_json_to_markdown_document as json2md
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from langchain_core.documents import Document

from config import SUPABASE, COLLECTION, CHUNK_SIZE, CHUNK_OVERLAP
from .get.data import get_company_id

def interaction_id(talking_product_id: str, date: str, time: str, question: str) -> str:
    q_hash = hashlib.md5(question.encode("utf-8")).hexdigest()
    return f"i_{talking_product_id}_{date}_{time}_{q_hash}"

def report_chunk_id(talking_product_id: str, report_type: str, date_key: str, chunk_idx: int) -> str:
    # date_key could be "2025-12-15" for daily or "2025-12-01_2025-12-31" for ranges
    return f"r_{talking_product_id}_{report_type}_{date_key}_c{chunk_idx:03d}"

def update_db_interactions(data, company_id=None, talking_product_id=None):
    """Insert interactions into Supabase and Chroma Cloud."""
    for log in data["logs"]:
        Q = log["question"]
        A = log["answer"]
        S = log["match_score"]
        D = log["date"]
        T = log["time"]
        # L = log["language"]
        E = log["embedding"]

        # 1️⃣ Supabase insert (Relational DB)
        # Commented out since we now have Prifina's ingestion!
        # try:
        #     SUPABASE.table("interactions").insert({
        #         "date": D,
        #         "time": T,
        #         "question": Q,
        #         "answer": A,
        #         "match_score": S,
        #         "language": L,
        #         "talking_product_id": talking_product_id
        #     }).execute()
        # except Exception as e:
        #     print(f"⚠️ Duplicate or error: {Q[:30]}... {e}")

        # 2️⃣ Chroma Cloud (Vector DB)
        COLLECTION.upsert(
            ids=[interaction_id(talking_product_id, D, T, Q)],
            documents=[f"Q: {Q}\nA: {A}"],   # better than Q alone
            metadatas=[{
                "doc_type": "interaction",
                "company_id": company_id,
                "talking_product_id": talking_product_id,
                "date": D,
                "time": T,
                "match_score": S,
                # "language": L
            }],
            embeddings=[E]
        )
        
    print(f"✅ Stored {len(data['logs'])} questions in both Relational and Vector DB for {data['date']}")
    return

def upsert_report_to_chroma(
    report: Any,
    company_id: str,
    talking_product_id: str,
    report_type: str,
    date: str,
    embed_fn,
    date_range: tuple = None
):
    # 1) Convert pydantic/dict → plain dict for json2md
    r = report.model_dump() if hasattr(report, "model_dump") else report

    # 2) Dict → markdown string (schema-agnostic)
    md_report: str = json2md(r)

    # 3) Use LangChain's MarkdownHeaderTextSplitter to split by headers
    # Only split on level-1 headers ('#') – add ('##', 'Subsection') etc. if you want deeper
    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "section_title")]
    )
    md_docs: List[Document] = md_splitter.split_text(md_report)

    # 4) Add base metadata
    base_metadata: Dict[str, Any] = {
        "doc_type": "report_chunk",
        "company_id": company_id,
        "talking_product_id": talking_product_id,
        "report_type": report_type,
        "date": date,
        "date_range": date_range,
    }

    # Each md_doc has .page_content (section text) and .metadata["section_title"]
    texts: List[str] = []
    metadatas: List[Dict[str, Any]] = []

    for section_idx, doc in enumerate(md_docs):
        section_title = doc.metadata.get("section_title")
        meta = {
            **base_metadata,
            "section_index": section_idx,
            "section_title": section_title,
        }
        texts.append(doc.page_content)
        metadatas.append(meta)

    # 5) Recursive splitter per section (won't split if below CHUNK_SIZE)
    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    docs: List[Document] = recursive_splitter.create_documents(
        texts=texts,
        metadatas=metadatas,
    )

    # 6) Prepare ids, contents, metadata, embeddings
    ids: List[str] = []
    documents: List[str] = []
    metadatas_for_chroma: List[Dict[str, Any]] = []
    embeddings: List[List[float]] = []

    for idx, doc in enumerate(docs):
        ids.append(report_chunk_id(talking_product_id, report_type, date, idx))
        documents.append(doc.page_content)
        metadatas_for_chroma.append(doc.metadata)
        if embed_fn:
            embeddings.append(embed_fn(doc.page_content))

    COLLECTION.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas_for_chroma,
        embeddings=embeddings if embeddings else None,
    )

def update_db_reports(data, report, embed_fn, report_type="Daily", company_id=None, talking_product_id=None, date_range=None):
    """
    Save the generated daily report into the Relational database.
    data is the dict from parse_email()
    report is the markdown string generated by the LLM
    report_type is one of "Daily", "Weekly", "Monthly" or "aggregated"
    """
    # Base fields shared by all report tables
    payload = {
        "date": data["date"],
        "n_logs": data["n_logs"],
        "average_match": data["average_match"],
        "complete_misses": data["complete_misses"],
        "complete_misses_rate": data["complete_misses_rate"],
        "report": report.model_dump(),
        "talking_product_id": talking_product_id
    }

    # Only add company fields if using the aggregated table
    if report_type == "aggregated":
        payload["date_range"] = date_range
        payload["company_id"] = company_id

    # Insert or replace the report
    try:
        SUPABASE.table(report_type).upsert(payload).execute()
    except Exception as e:
        print(f"⚠️ Error saving report for {data['date']}: {e}")
        return
    upsert_report_to_chroma(report, company_id, talking_product_id, report_type, data['date'], embed_fn, date_range)
    print(f"✅ Saved report for {data['date']}")
    return

def add_company(name: str):
    """Add a company name and return its id."""
    ins = (
        SUPABASE.table("companies")
        .insert({"name": name})
        .execute()
    )
    return ins.data[0]["id"]

def add_talking_product(company_name: str, product_name: str, admin_url=None, url=None, qr_code=None):
    """Insert a talking product by company name, fetch company id first."""
    # 1) Get company id
    company_id = get_company_id(company_name)

    # 2) Build insert payload
    payload = {
        "company_id": company_id,
        "name": product_name,
        "admin_url": admin_url,
        "url": url,
        "qr_code": qr_code
    }

    # 3) Insert talking product (ignore if exists)
    ins = (
        SUPABASE.table("talking_products")
        .insert(payload)
        .execute()
    )

    return ins.data[0]["id"]



if __name__ == "__main__":
    # run store.py directly to add a company and its talking products from env vars
    company = os.getenv("COMPANY_NAME")
    company_id = get_company_id(company)
    if company_id is None:
        company_id = add_company(company)
    talking_products = os.getenv("TALKING_PRODUCTS").split(",")
    admin_urls = os.getenv("TALKING_PRODUCT_ADMIN_URLS", "").split(",")
    urls = os.getenv("TALKING_PRODUCT_URLS", "").split(",")
    qr_codes = os.getenv("TALKING_PRODUCT_QR_CODES", "").split(",")
    for i, p in enumerate(talking_products):
        admin_url = admin_urls[i] if i < len(admin_urls) else None
        url = urls[i] if i < len(urls) else None
        qr_code = qr_codes[i] if i < len(qr_codes) else None
        add_talking_product(company, p, admin_url=admin_url, url=url, qr_code=qr_code)