from typing import TypedDict


class State(TypedDict, total=False):
    # NOTE: raw document text is deliberately NOT part of the state. State is
    # checkpointed and visible to tracing, so only masked content may live here.
    input_path: str
    question: str          # sales analytics question
    session_id: str        # key into the encrypted PII vault
    doc_type: str          # "protocol" | "sales"
    masked_doc: str        # masked protocol text
    masked_path: str       # masked CSV path (sales)
    compliance: dict       # counts + verdict, never values
    result: dict
    validation: dict
    attempts: int
    feedback: str
    errors: list
