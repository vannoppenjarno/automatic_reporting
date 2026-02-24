from datetime import date
from typing import Optional, Tuple

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.prompt import answer_with_rag, answer_with_sql, answer_directly
from config import SUPABASE

# ----------------- Setup -----------------

# python -m uvicorn backend:app --reload
# Which topic is most frequently asked?
# What are the most important takeaways from this report?


app = FastAPI(title="Digiole Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:5500", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------- Pydantic models -----------------

class AskRequest(BaseModel):
    company_id: str
    talking_product_id: Optional[str] = None
    date_range: Optional[Tuple[date, date]] = None
    question: str

class AskResponse(BaseModel):
    answer: str  


# ----------------- Data helpers (tenant-aware) -----------------

def ensure_product_belongs_to_company(talking_product_id: str, company_id: str):
    res = (
        SUPABASE.table("talking_products")
        .select("id")
        .eq("id", talking_product_id)
        .eq("company_id", company_id)
        .eq("active", True)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Talking product not found for this company",
        )


# ----------------- RAG / SQL / Q&A endpoint (tenant-safe) -----------------
@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    print("ASK CALLED")
    print(req)
    if req.talking_product_id:
        ensure_product_belongs_to_company(req.talking_product_id, req.company_id)

    all_products = not req.talking_product_id
    all_time = not req.date_range

    if all_products or all_time:
        resp = answer_with_sql(req.question, req.company_id)  # or answer_with_rag(...)
    else:
        resp = answer_directly(req.question, req.company_id, req.talking_product_id, req.date_range)
        
    answer_text = resp.content if hasattr(resp, "content") else str(resp)
    print(answer_text)
    return AskResponse(answer=answer_text)

