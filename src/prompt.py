from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from .report import Report

from .get.templates import get_daily_prompt_template, get_rag_prompt, get_context
from .get.models import get_llm_model

def create_report_chain():
    """
    Build a LangChain pipeline:
        context + logs_text + format_instructions
        -> ChatGoogleGenerativeAI
        -> PydanticOutputParser(Report)

    Returns:
        chain: Runnable that takes {"logs_text": "..."} and returns a Report instance
    """
    parser = PydanticOutputParser(pydantic_object=Report)
    template_str = get_daily_prompt_template()  # Prompt template – loaded from markdown file
    prompt = ChatPromptTemplate.from_template(template_str)
    llm = get_llm_model()

    # 4) Build chain:
    #    - supply context + logs_text + format_instructions as inputs
    #    - prompt formats them
    #    - LLM generates text
    #    - parser turns it into Report
    chain = (
        {
            "context": lambda _: get_context(),
            "logs_text": lambda x: x["logs_text"],
            "format_instructions": lambda _: parser.get_format_instructions(),
        }
        | prompt
        | llm
        | parser
    )

    return chain

def generate_report(logs_text: str) -> Report:
    """
    Generate a structured Report from logs_text using:
        - ChatGoogleGenerativeAI via LangChain
        - ChatPromptTemplate loaded from file
        - PydanticOutputParser(Report)

    Returns:
        Report instance (Pydantic model)
    """
    chain = create_report_chain()
    # The chain expects an input dict with "logs_text" and internally fills context + format_instructions.
    try:
        report: Report = chain.invoke({"logs_text": logs_text})
        return report
    except Exception as e:
        # Optional: if you want a manual fallback instead of hard failure, you can log e here and rethrow or return a minimal object.
        raise RuntimeError(f"Failed to generate report: {e}")
    
def answer_with_rag(question: str, context: str):
    rag_prompt = ChatPromptTemplate.from_template(get_rag_prompt())
    llm = get_llm_model()
    chain = rag_prompt | llm
    return chain.invoke({"question": question, "context": context})
