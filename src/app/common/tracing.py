"""Phoenix (Arize) tracing, self-hosted. Auto-instruments LangChain/LangGraph:
nodes, LLM calls, retries, token usage."""
from .config import settings


def init_tracing() -> None:
    from openinference.instrumentation.langchain import LangChainInstrumentor
    from phoenix.otel import register

    provider = register(project_name=settings.phoenix_project,
                        endpoint=settings.phoenix_endpoint, auto_instrument=False)
    LangChainInstrumentor().instrument(tracer_provider=provider)
