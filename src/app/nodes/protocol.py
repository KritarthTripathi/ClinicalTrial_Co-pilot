import re

from pydantic import BaseModel, Field

from ..config import settings
from ..llm import get_llm

HEADING = re.compile(r"^\s*(\d+(?:\.\d+)*\.?)\s+([A-Z][A-Za-z /&-]{3,})\s*$")
RELEVANT = re.compile(r"inclusion|exclusion|endpoint|objective|schedule|dosing|treatment|design", re.I)


class ProtocolExtraction(BaseModel):
    title: str
    phase: str | None = None
    inclusion_criteria: list[str] = Field(default_factory=list)
    exclusion_criteria: list[str] = Field(default_factory=list)
    primary_endpoints: list[str] = Field(default_factory=list)
    secondary_endpoints: list[str] = Field(default_factory=list)
    visits: list[str] = Field(default_factory=list)
    dosing: str | None = None


def chunk_by_section(text: str) -> list[tuple[str, str]]:
    """Section-aware chunking: split on numbered headings, not fixed sizes."""
    chunks, head, buf = [], "preamble", []
    for line in text.split("\n"):
        m = HEADING.match(line)
        if m:
            chunks.append((head, "\n".join(buf)))
            head, buf = m.group(2), [line]
        else:
            buf.append(line)
    chunks.append((head, "\n".join(buf)))
    return [c for c in chunks if c[1].strip()]


def protocol_node(state: dict) -> dict:
    chunks = chunk_by_section(state["masked_doc"])
    picked = [body for head, body in chunks if RELEVANT.search(head)] or [c[1] for c in chunks]
    context = "\n\n".join(picked)[: settings.max_context_chars]

    prompt = (
        "Extract structured data from this clinical trial protocol excerpt. "
        "Copy criteria and endpoints verbatim; do not invent anything. "
        "Placeholders like <PERSON_1> are intentional; keep them as-is.\n"
    )
    if state.get("feedback"):
        prompt += f"Previous attempt had problems, fix them: {state['feedback']}\n"
    llm = get_llm("extract").with_structured_output(ProtocolExtraction)
    result = llm.invoke(prompt + "\n---\n" + context)
    return {"result": result.model_dump(), "attempts": state.get("attempts", 0) + 1}
