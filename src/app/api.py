from datetime import date
from typing import List, Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from src.prompt import answer_with_rag
from src.get.data import retrieve_context
from config import SUPABASE, RETRIEVAL_K, REPORT_TABLES, GOOGLE_CLIENT_ID

# ----------------- Setup -----------------

app = FastAPI(title="Digiole Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------- Pydantic models -----------------

class User(BaseModel):
    id: str
    email: str
    company_id: str

class TalkingProduct(BaseModel):
    id: str
    name: str
    company_id: str
    active: bool

class Report(BaseModel):
    report: dict  # just wrap the raw JSON

class AskRequest(BaseModel):
    talking_product_id: Optional[str] = None
    question: str

class AskResponse(BaseModel):
    answer: str
    citations: list

# ----------------- Auth / multi-tenant -----------------

def verify_google_token(id_token_str: str) -> dict:
    """
    Verify Google ID token and return decoded payload.
    """
    try:
        idinfo = id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google ID token",
        )

    if idinfo.get("iss") not in (
        "accounts.google.com",
        "https://accounts.google.com",
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token issuer",
        )
    return idinfo


def get_or_create_user(google_sub: str, email: str):
    res = (
        SUPABASE.table("users")
        .select("*")
        .eq("google_sub", google_sub)
        .limit(1)
        .execute()
    )

    if res.data:
        return res.data[0]

    # create new user without company_id
    new_user = {
        "email": email,
        "google_sub": google_sub,
        "company_id": None
    }

    created = SUPABASE.table("users").insert(new_user).execute()
    return created.data[0]


async def get_current_user(authorization: str = Header(..., description="Bearer <google_id_token>")) -> User:
    """
    FastAPI dependency:
    - Reads Google ID token from Authorization header
    - Verifies it
    - Loads matching user + company from Supabase
    """
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be 'Bearer <token>'",
        )

    idinfo = verify_google_token(token)
    google_sub = idinfo["sub"]
    email = idinfo.get("email", "")

    user = get_or_create_user(google_sub, email)
    if not user["company_id"]:
        raise HTTPException(403, "User not linked to a company yet")
    
    return user


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


# ----------------- Endpoints -----------------

@app.get(
    "/me/talking-products",
    response_model=List[TalkingProduct],
    summary="List talking products for the logged-in user's company",
)
def list_my_talking_products(current_user: User = Depends(get_current_user)):
    res = (
        SUPABASE.table("talking_products")
        .select("id,name,company_id,active")
        .eq("company_id", current_user.company_id)
        .eq("active", True)
        .execute()
    )
    return res.data or []


@app.get(
    "/reports",
    response_model=Report,
    summary="Fetch report JSON for logged-in user's company",
)
def get_report(
    report_type: Literal["daily", "weekly", "monthly", "aggregated"] = Query(...),
    report_date: date = Query(..., description="YYYY-MM-DD"),
    talking_product_id: Optional[str] = Query(
        None,
        description="Required for daily/weekly/monthly. For aggregated you can omit if company-level.",
    ),
    current_user: User = Depends(get_current_user),
):
    table = REPORT_TABLES[report_type]

    if report_type in ("daily", "weekly", "monthly"):
        if not talking_product_id:
            raise HTTPException(400, "talking_product_id is required for this report type")
        ensure_product_belongs_to_company(talking_product_id, current_user.company_id)

        res = (
            SUPABASE.table(table)
            .select("report")
            .eq("talking_product_id", talking_product_id)
            .eq("date", report_date.isoformat())
            .limit(1)
            .execute()
        )

    else:  # aggregated
        # aggregated already has company_id + talking_product_id
        query = (
            SUPABASE.table(table)
            .select("report")
            .eq("company_id", current_user.company_id)
            .eq("date", report_date.isoformat())
        )
        if talking_product_id:
            ensure_product_belongs_to_company(talking_product_id, current_user.company_id)
            query = query.eq("talking_product_id", talking_product_id)

        res = query.limit(1).execute()

    rows = res.data or []
    if not rows:
        raise HTTPException(404, "Report not found")

    return Report(report=rows[0]["report"])


# ----------------- RAG Q&A endpoint (tenant-safe) -----------------

@app.post(
    "/ask",
    response_model=AskResponse,
    summary="Ask a question about your company's reports/interactions",
)
def ask_rag(
    req: AskRequest,
    current_user: User = Depends(get_current_user),
):
    # If a talking_product_id is provided, enforce tenant check
    if req.talking_product_id:
        ensure_product_belongs_to_company(req.talking_product_id, current_user.company_id)

    context, citations = retrieve_context(
        query=req.question,
        company_id=current_user.company_id,
        talking_product_id=req.talking_product_id,
        k=RETRIEVAL_K,
    )

    resp = answer_with_rag(req.question, context)

    answer_text = resp.content if hasattr(resp, "content") else str(resp)

    return AskResponse(
        answer=answer_text,
        citations=citations,
    )
