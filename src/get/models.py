from sentence_transformers import SentenceTransformer
from langchain_google_genai import ChatGoogleGenerativeAI
from config import EMBED_MODEL, LLM_MODEL, LLM_API_KEY


def get_embed_model(embed_model: str = EMBED_MODEL):
    return SentenceTransformer(embed_model)

def get_llm_model(llm_model: str = LLM_MODEL):
    # Placeholder for LLM model retrieval logic
    # Gemini LLM via LangChain
    return ChatGoogleGenerativeAI(
        model=llm_model,
        temperature=0,
        max_retries=5,        # built-in retry for transient errors
        google_api_key=LLM_API_KEY  # optional; uses env var by default
    )