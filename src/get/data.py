
from config import SUPABASE, COLLECTION, RETRIEVAL_K, READONLY_SQL_RPC
from typing import List, Dict, Any
from datetime import datetime
from src.embed import embed_fn

def get_active_company_ids():
    """
    Fetch all active company IDs from the companies table.
    Returns a list of company IDs.
    """
    res = (
        SUPABASE.table("companies")
        .select("id")
        .eq("active", True)
        .execute()
    )

    rows = res.data or []
    return [r["id"] for r in rows]

def get_company_id(name: str):
    """Fetch company id by name, return None if not found."""
    res = (
        SUPABASE.table("companies")
        .select("id")
        .eq("name", name)
        .maybe_single()
        .execute()
    )
    return res.data["id"] if res.data else None

def get_active_talking_product_ids(company_id: str):
    """
    Fetch all active talking products for a given company_id.
    Returns a list of talking product IDs.
    """
    res = (
        SUPABASE.table("talking_products")
        .select("id")
        .eq("company_id", company_id)
        .eq("active", True)
        .execute()
    )

    rows = res.data or []
    return [r["id"] for r in rows]

def get_ids(talking_product_name: str):
    """
    Return (talking_product_id, company_id) for a given talking_product_name.
    Returns (None, None) if not found.
    """
    res = (
        SUPABASE.table("talking_products")
        .select("id, company_id")
        .eq("name", talking_product_name)
        .maybe_single()
        .execute()
    )

    if not res.data:
        return None, None
    
    return res.data["id"], res.data["company_id"]

def get_latest_interaction_date(talking_product_id):
    """
    Fetch latest interaction date for a given talking_product_id.
    Returns a date object or None.
    """
    res = (
        SUPABASE.table("interactions")
        .select("date")
        .eq("talking_product_id", talking_product_id)
        .order("date", desc=True)
        .limit(1)
        .execute()
    )

    data = res.data 
    if not data:
        return None

    return datetime.strptime(data[0]["date"], "%Y-%m-%d").date()

def retrieve_context(query: str, company_id: str, talking_product_id: str | None, embed_fn = embed_fn, k: int = RETRIEVAL_K, date=None, start_date=None, end_date=None):
    q_emb = embed_fn(query)

    clauses = [{"company_id": company_id}]
    if talking_product_id is not None:
        clauses.append({"talking_product_id": talking_product_id})

    if date is not None:
        clauses.append({"date": date})

    if start_date is not None and end_date is not None:
        clauses.append({"date": {"$gte": start_date, "$lte": end_date}})

    # --- Build final WHERE ---
    if len(clauses) == 1:
        where = clauses[0]        # single filter → don't wrap in $and
    else:
        where = {"$and": clauses} # multiple filters → Chroma requires $and

    # TODO: filter by report_type if needed and by doc_type!!!

    res = COLLECTION.query(
        query_embeddings=[q_emb],
        n_results=k,
        where=where,
        include=["documents", "metadatas", "distances"]
    )

    docs = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res.get("distances", [[None]*len(docs)])[0]

    # Build compact context + citations
    context_blocks = []
    citations = []
    for i, (doc, meta, dist) in enumerate(zip(docs, metas, dists), start=1):
        tag = meta.get("doc_type", "doc")
        tp = meta.get("talking_product_id", "")
        rk = meta.get("date_key") or meta.get("date")
        context_blocks.append(f"[{i}] ({tag}, tp={tp}, date={rk})\n{doc}")
        citations.append({"i": i, "meta": meta, "distance": dist})

    return "\n\n".join(context_blocks), citations

def fetch_questions(date_range, talking_product_id=None, company_id=None):
    """
    Fetch questions (and compute summary statistics) from Supabase within optional date range based on:
    1) talking_product_id (if provided)
    2) otherwise company_id (fetch all products under company)

    Returns a dict identical in structure to parse_email() output:
    {
        "date": "<start_date>",
        "n_logs": int,
        "average_match": float,
        "complete_misses": int,
        "complete_misses_rate": float,
        "logs": [ {question, answer, match_score, time, embedding}, ... ]
    }
    """
    # Determine date bounds
    if date_range:
        start_date, end_date = date_range
        if hasattr(start_date, "isoformat"): start_date = start_date.isoformat()
        if hasattr(end_date, "isoformat"): end_date = end_date.isoformat()
    else:
        start_date, end_date = None, None

    params = {
        "_talking_product_id": talking_product_id,
        "_company_id": company_id,
        "_start_date": start_date,
        "_end_date": end_date
    }
    # Call RPC
    try:
        rows = rpc_paginate("fetch_interactions_filtered", params, batch_size=1000)
        logs, accumulated_match, complete_misses = [], 0.0, 0

        for r in rows:
            s = float(r.get("match_score", 0))

            logs.append({
                "question": r["question"],
                "answer": r["answer"],
                "match_score": s,
                "date": r["date"],
                "time": r["interaction_time"],
            })

            accumulated_match += s
            if s == 0:
                complete_misses += 1

        n_logs = len(logs)
        avg_match = round(accumulated_match / n_logs, 2) if n_logs > 0 else 0
        complete_misses_rate = round((complete_misses / n_logs) * 100, 2) if n_logs > 0 else 0

        if start_date is None:
            start_date = datetime.today().date().isoformat()  # Save generation date if no range provided
            end_date = start_date

        data = {
            "date": start_date,
            "n_logs": n_logs,
            "average_match": avg_match,
            "complete_misses": complete_misses,
            "complete_misses_rate": complete_misses_rate,
            "logs": logs
        }

        print(
            f"✅ {n_logs} logs | Product={talking_product_id} | Company={company_id} "
            f"| Range: {start_date} → {end_date} | Avg: {avg_match}% | Misses: {complete_misses}"
        )
        return data

    except Exception as e:
        print(f"⚠️ Error fetching questions from {start_date} → {end_date}: {e}")
        return {
            "date": start_date,
            "n_logs": 0,
            "average_match": 0,
            "complete_misses": 0,
            "complete_misses_rate": 0,
            "logs": []
        }

def rpc_paginate(rpc_name, params, batch_size=1000):
    """Helper to paginate through Supabase RPC calls with _limit and _offset."""
    all_rows = []
    offset = 0

    while True:
        chunk_params = params.copy()
        chunk_params["_limit"] = batch_size
        chunk_params["_offset"] = offset

        res = SUPABASE.rpc(rpc_name, chunk_params).execute()
        data = res.data or []

        if not data:
            break

        all_rows.extend(data)
        offset += batch_size

        if len(data) < batch_size:
            break

    return all_rows

def execute_readonly_sql(sql: str, rpc_name: str = READONLY_SQL_RPC) -> List[Dict[str, Any]]:
    try:
        res = SUPABASE.rpc(rpc_name, {"query": sql}).execute()
    except Exception as e:
        raise RuntimeError(f"SQL execution failed via RPC '{rpc_name}': {e}")

    return res.data or []
