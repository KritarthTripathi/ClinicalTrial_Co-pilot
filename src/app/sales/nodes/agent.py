"""Sales agent steps. The database holds only masked values, so nothing here sees real names."""
import json
import re
from decimal import Decimal
from pathlib import Path

import duckdb

from app.common.config import settings
from app.common.llm import get_llm
from app.sales.semantic.catalog import EXAMPLES, KEYWORDS, METRICS_TEXT, TEMPLATE, VIEWS
from app.sales.sql_guard import guard

DB = Path(settings.work_dir) / "pharma.duckdb"
COUNT_COLS = re.compile(r"trx|nrx|nbrx|calls|vae|submitted|paid|rejected|abandoned|count", re.I)


def connect():
    con = duckdb.connect(str(DB), read_only=True)
    try:
        con.execute("SET enable_external_access=false")
    except Exception:
        pass
    return con


def _json_default(o):
    return float(o) if isinstance(o, Decimal) else str(o)


def extract_sql(text: str) -> str:
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S | re.I)
    text = m.group(1) if m else text
    m = re.search(r"\b(select|with)\b", text, re.I)
    return text[m.start():].strip() if m else text.strip()


def select_views_node(state):
    q = state["question"].lower()
    chosen = [v for v, kws in KEYWORDS.items() if any(k in q for k in kws)]
    if "v_hcp_rx" in chosen and "v_hcp_activity" in chosen:
        chosen = ["v_hcp_monthly"] + chosen
    con = connect()
    data_end = str(con.execute("SELECT MAX(week_start) FROM fact_rx").fetchone()[0])
    con.close()
    return {"views": chosen or list(VIEWS), "data_end": data_end, "attempts": 0, "error": ""}


def write_sql_node(state):
    views = "\n".join(f"- {v}: {VIEWS[v]['desc']} Columns: {VIEWS[v]['cols']}" for v in state["views"])
    prompt = TEMPLATE.format(views=views, metrics=METRICS_TEXT, data_end=state["data_end"],
                             examples=EXAMPLES, question=state["question"])
    if state.get("error"):
        prompt += f" {state.get('sql_raw', '')[:400]}\n(That attempt failed: {state['error']}. Write a corrected query.)\nSQL:"
    raw = get_llm("sql").invoke(prompt).content
    return {"sql_raw": extract_sql(raw), "attempts": state.get("attempts", 0) + 1, "error": ""}


def guard_node(state):
    try:
        return {"sql": guard(state["sql_raw"]), "error": ""}
    except Exception as e:
        return {"error": f"SQL rejected: {e}"}


def execute_node(state):
    try:
        con = connect()
        res = con.execute(state["sql"])
        cols = [d[0] for d in res.description]
        rows = res.fetchmany(200)
        con.close()
        return {"columns": cols, "rows": json.loads(json.dumps(rows, default=_json_default)), "error": ""}
    except Exception as e:
        return {"error": f"SQL error: {str(e)[:300]}"}


def validate_node(state):
    rows, cols = state.get("rows", []), state.get("columns", [])
    if not rows:
        return {"error": "query returned no rows; check filters and date ranges"}
    for j, c in enumerate(cols):
        if COUNT_COLS.search(c) and any(isinstance(r[j], (int, float)) and r[j] < 0 for r in rows):
            return {"error": f"negative values in count column {c}"}
    return {"error": ""}


def _fmt(v):
    return round(v, 4) if isinstance(v, float) else v


def render_table(cols, rows, n=20):
    lines = [" | ".join(cols)] + [" | ".join(str(_fmt(v)) for v in r) for r in rows[:n]]
    if len(rows) > n:
        lines.append(f"... {len(rows) - n} more rows")
    return "\n".join(lines)


def _nums(s):
    out = []
    for x in re.findall(r"(?<![A-Za-z0-9])\d[\d,]*\.?\d*", s):
        try:
            out.append(float(x.replace(",", "").rstrip(".")))
        except ValueError:
            pass
    return out


def grounded(narration, table):
    allowed = _nums(table)
    return all(any(abs(x - y) <= max(0.01 * abs(y), 0.006) for y in allowed) or x in (1, 2, 3) for x in _nums(narration))


def narrate_node(state):
    table = render_table(state["columns"], state["rows"])
    if state.get("skip_narrate"):
        return {"table": table, "answer": ""}
    prompt = (f"Question: {state['question']}\nResults:\n{table}\n"
              "Answer in one or two short sentences using only numbers shown in the results. "
              "Keep placeholders like <FULL_NAME_3> exactly as written.")
    text = get_llm("router").invoke(prompt).content.strip()
    return {"table": table, "answer": text if grounded(text, table) else "(summary skipped: numbers could not be verified; see table)"}
