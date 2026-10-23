import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph

from app.common.config import settings
from .nodes.ingest_mask import ingest_mask_node
from .nodes.protocol import protocol_node
from .nodes.validator import validator_node
from .state import State


def route_after_compliance(state: State) -> str:
    return "protocol" if state["compliance"]["verdict"] == "pass" else "blocked"


def route_after_validation(state: State) -> str:
    v = state["validation"]
    return "done" if v["ok"] or not v["will_retry"] else "protocol"


def build_graph():
    g = StateGraph(State)
    g.add_node("ingest_mask", ingest_mask_node)
    g.add_node("protocol", protocol_node)
    g.add_node("validator", validator_node)

    g.set_entry_point("ingest_mask")
    g.add_conditional_edges("ingest_mask", route_after_compliance,
                            {"protocol": "protocol", "blocked": END})
    g.add_edge("protocol", "validator")
    g.add_conditional_edges("validator", route_after_validation,
                            {"protocol": "protocol", "done": END})

    Path(settings.checkpoint_db).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.checkpoint_db, check_same_thread=False)
    return g.compile(checkpointer=SqliteSaver(conn))