from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from .report import Report

from .get.templates import get_daily_prompt_template, get_rag_prompt, get_context
from .get.models import get_llm_model

# 1) Build shared objects ONCE
parser = PydanticOutputParser(pydantic_object=Report)
DAILY_PROMPT_TEMPLATE = get_daily_prompt_template()
DAILY_PROMPT = ChatPromptTemplate.from_template(DAILY_PROMPT_TEMPLATE)

RAG_PROMPT_TEMPLATE = get_rag_prompt()
RAG_PROMPT = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)

LLM = get_llm_model()  # single LLM instance


# 2) Build the chains ONCE
REPORT_CHAIN = (
    {
        "context": lambda _: get_context(),
        "logs_text": lambda x: x["logs_text"],
        "format_instructions": lambda _: parser.get_format_instructions(),
    }
    | DAILY_PROMPT
    | LLM
    | parser
)

RAG_CHAIN = RAG_PROMPT | LLM


def generate_report(logs_text: str) -> Report:
    """Use the pre-built REPORT_CHAIN."""
    try:
        report: Report = REPORT_CHAIN.invoke({"logs_text": logs_text})
        return report
    except Exception as e:
        raise RuntimeError(f"Failed to generate report: {e}")


def answer_with_rag(question: str, context: str):
    """Use the pre-built RAG_CHAIN."""
    return RAG_CHAIN.invoke({"question": question, "context": context})
