import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph

from .config import settings
from .nodes.ingest_mask import ingest_mask_node
from .nodes.protocol import protocol_node
from .nodes.sales import sales_node
from .nodes.validator import validator_node
from .state import State


def route_after_compliance(state: State) -> str:
    if state["compliance"]["verdict"] != "pass":
        return "blocked"          # swap for a LangGraph interrupt() for human review
    return state["doc_type"]


def route_after_validation(state: State) -> str:
    if state["validation"]["ok"] or not state["validation"]["will_retry"]:
        return "done"
    return state["doc_type"]      # bounded retry loop back to the specialist


def build_graph():
    g = StateGraph(State)
    g.add_node("ingest_mask", ingest_mask_node)
    g.add_node("protocol", protocol_node)
    g.add_node("sales", sales_node)
    g.add_node("validator", validator_node)

    g.set_entry_point("ingest_mask")
    g.add_conditional_edges("ingest_mask", route_after_compliance,
                            {"protocol": "protocol", "sales": "sales", "blocked": END})
    g.add_edge("protocol", "validator")
    g.add_edge("sales", "validator")
    g.add_conditional_edges("validator", route_after_validation,
                            {"protocol": "protocol", "sales": "sales", "done": END})

    Path(settings.checkpoint_db).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.checkpoint_db, check_same_thread=False)
    return g.compile(checkpointer=SqliteSaver(conn))
