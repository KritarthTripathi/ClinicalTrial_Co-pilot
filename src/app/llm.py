"""LLM is a config choice. Swap ChatOllama for another backend here and nowhere else."""
from langchain_ollama import ChatOllama

from .config import settings


def get_llm(role: str = "extract") -> ChatOllama:
    model = settings.router_model if role == "router" else settings.extract_model
    return ChatOllama(model=model, base_url=settings.ollama_base_url, temperature=0, num_ctx=4096)
