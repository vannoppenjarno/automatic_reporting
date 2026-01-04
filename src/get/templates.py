from config import CONTEXT_PATH, DAILY_PROMPT_TEMPLATE_PATH, RAG_PROMPT_TEMPLATE_PATH

def get_context():
    """
    Load context from a markdown file.
    """
    with open(CONTEXT_PATH, 'r', encoding="utf-8") as file:
        context = file.read()
    return context

def get_daily_prompt_template():
    """
    Load the daily prompt template from a markdown file.
    """
    with open(DAILY_PROMPT_TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return f.read()
    
def get_rag_prompt():
    """
    Load RAG prompt template from file.
    """
    with open(RAG_PROMPT_TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return f.read()
