import re

from pydantic import BaseModel, Field

from app.common.config import settings
from app.common.llm import get_llm

HEADING = re.compile(r"^\s*(\d+(?:\.\d+)*\.?)\s+([A-Z][A-Za-z /&-]{3,})\s*$")
RELEVANT = re.compile(r"inclusion|exclusion|endpoint|objective|schedule|dosing|treatment|design", re.I)


class Items(BaseModel):
    items: list[str] = Field(default_factory=list)


class Endpoints(BaseModel):
    primary: list[str] = Field(default_factory=list)
    secondary: list[str] = Field(default_factory=list)


class Dosing(BaseModel):
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


def _section(chunks, pattern: str) -> str:
    return "\n".join(body for head, body in chunks if re.search(pattern, head, re.I))


def _ask(schema, instruction: str, text: str, feedback: str = ""):
    if not text.strip():
        return schema()
    prompt = instruction + " Copy wording from the text. Never invent anything."
    if feedback:
        prompt += f" A previous attempt had problems: {feedback}"
    llm = get_llm("extract").with_structured_output(schema)
    return llm.invoke(prompt + "\n---\n" + text[: settings.max_context_chars])


def protocol_node(state: dict) -> dict:
    doc = state["masked_doc"]
    chunks = chunk_by_section(doc)
    fb = state.get("feedback", "")

    incl = _ask(Items, "List each inclusion criterion as one short string.", _section(chunks, "inclusion"), fb)
    excl = _ask(Items, "List each exclusion criterion as one short string.", _section(chunks, "exclusion"), fb)
    visits = _ask(Items, "List each visit or timepoint named in this schedule.", _section(chunks, "schedule"), fb)
    ends = _ask(Endpoints, "Extract the primary and secondary endpoints.", _section(chunks, "endpoint"), fb)
    dose = _ask(Dosing, "Summarize the dosing regimen in one sentence.", _section(chunks, "dosing"), fb)

    first = next((l.strip() for l in doc.split("\n") if l.strip()), "")
    phase = re.search(r"Phase\s+(IV|I{1,3}|\d)", doc, re.I)
    result = {
        "title": first,
        "phase": phase.group(1) if phase else None,
        "inclusion_criteria": incl.items,
        "exclusion_criteria": excl.items,
        "primary_endpoints": ends.primary,
        "secondary_endpoints": ends.secondary,
        "visits": visits.items,
        "dosing": dose.dosing,
    }
    return {"result": result, "attempts": state.get("attempts", 0) + 1}