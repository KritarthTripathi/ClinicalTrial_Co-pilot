import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph

from app.common.config import settings
from app.sales.nodes.agent import (execute_node, guard_node, narrate_node, select_views_node,
                                   validate_node, write_sql_node)
from app.sales.state import SalesState


def route(state):
    if not state.get("error"):
        return "ok"
    return "retry" if state.get("attempts", 0) <= settings.max_retries else "fail"


def build_graph():
    g = StateGraph(SalesState)
    for name, fn in [("select_views", select_views_node), ("write_sql", write_sql_node), ("guard", guard_node),
                     ("execute", execute_node), ("validate", validate_node), ("narrate", narrate_node)]:
        g.add_node(name, fn)
    g.set_entry_point("select_views")
    g.add_edge("select_views", "write_sql")
    g.add_edge("write_sql", "guard")
    g.add_conditional_edges("guard", route, {"ok": "execute", "retry": "write_sql", "fail": END})
    g.add_conditional_edges("execute", route, {"ok": "validate", "retry": "write_sql", "fail": END})
    g.add_conditional_edges("validate", route, {"ok": "narrate", "retry": "write_sql", "fail": END})
    g.add_edge("narrate", END)
    Path(settings.checkpoint_db).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.checkpoint_db, check_same_thread=False)
    return g.compile(checkpointer=SqliteSaver(conn))
