from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from .get.templates import get_daily_prompt, get_sql_prompt, get_llm_prompt, get_rag_prompt, get_context
from .get.data import execute_readonly_sql, retrieve_context 
from .get.models import get_llm_model, get_free_local_llm
from .utils import rows_to_context, validate_readonly_sql
from .report import Report


# Build shared objects ONCE
parser = PydanticOutputParser(pydantic_object=Report)
REPORT_INFO = {
        "context": lambda _: get_context(),
        "logs_text": lambda x: x["logs_text"],
        "format_instructions": lambda _: parser.get_format_instructions(),
    }


# Build prompt templates ONCE
DAILY_PROMPT = ChatPromptTemplate.from_template(get_daily_prompt())
SQL_PROMPT = ChatPromptTemplate.from_template(get_sql_prompt())
LLM_PROMPT = ChatPromptTemplate.from_template(get_llm_prompt())
RAG_PROMPT = ChatPromptTemplate.from_template(get_rag_prompt())


# Get LLM models ONCE
LLM = get_llm_model()  
FREE_LLM = get_free_local_llm()


# Build the chains ONCE
REPORT_CHAIN = REPORT_INFO | DAILY_PROMPT | LLM | parser
SQL_CHAIN = SQL_PROMPT | FREE_LLM
LLM_CHAIN = LLM_PROMPT | FREE_LLM
RAG_CHAIN = RAG_PROMPT | LLM


def generate_report(logs_text: str) -> Report:
    """Use the pre-built REPORT_CHAIN."""
    try:
        report: Report = REPORT_CHAIN.invoke({"logs_text": logs_text})
        return report
    except Exception as e:
        raise RuntimeError(f"Failed to generate report: {e}")


def answer_with_rag(question: str, company_id: str, talking_product_id: str):
    """Use the pre-built RAG_CHAIN."""
    context, citations = retrieve_context(
        query=question,
        company_id=company_id,
        talking_product_id=talking_product_id
    )
    return RAG_CHAIN.invoke({"question": question, "context": context}), citations


def generate_readonly_sql(question: str, company_id: str) -> str:
    resp = SQL_CHAIN.invoke(
        {
            "question": question,
            "company_id": company_id,
        }
    )
    raw_sql = resp.content if hasattr(resp, "content") else str(resp)
    return validate_readonly_sql(raw_sql)


def answer_with_sql(question: str, company_id: str):
    sql = generate_readonly_sql(question, company_id)
    rows = execute_readonly_sql(sql)
    context = rows_to_context(rows)
    print(sql)
    print(context)
    return LLM_CHAIN.invoke({"question": question, "sql": sql, "context": context})
