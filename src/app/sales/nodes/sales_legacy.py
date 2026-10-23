import json
import re

import duckdb

from app.common.llm import get_llm

FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|copy|pragma|install|load|export|call|set)\b", re.I)


def safe_sql(sql: str) -> str:
    s = sql.strip().strip("`").removeprefix("sql").strip().rstrip(";").strip()
    if ";" in s or not re.match(r"(?is)^(select|with)\b", s) or FORBIDDEN.search(s):
        raise ValueError("only a single read-only SELECT is allowed")
    return s


def sales_node(state: dict) -> dict:
    question = state.get("question") or "Total revenue by region and top 3 products by units."
    con = duckdb.connect(":memory:")
    con.execute(f"CREATE TABLE sales AS SELECT * FROM read_csv_auto('{state['masked_path']}')")
    con.execute("SET enable_external_access=false")   # no file/network access from model SQL
    schema = con.execute("DESCRIBE sales").fetchall()
    sample = con.execute("SELECT * FROM sales LIMIT 3").fetchall()

    prompt = (
        "Write ONE DuckDB SQL SELECT query against table `sales` to answer the question. "
        "Return only SQL, no commentary.\n"
        f"Schema (name, type, ...): {[s[:2] for s in schema]}\nSample rows: {sample}\n"
    )
    if state.get("feedback"):
        prompt += f"Previous attempt failed: {state['feedback']}\n"
    prompt += f"Question: {question}"
    raw = get_llm("extract").invoke(prompt).content
    attempts = state.get("attempts", 0) + 1
    try:
        sql = safe_sql(raw)
        rows = con.execute(sql).fetchmany(50)
        cols = [d[0] for d in con.description]
        result = {"sql": sql, "columns": cols, "rows": json.loads(json.dumps(rows, default=str))}
    except Exception as e:  # surfaced to the validator, which triggers a bounded retry
        result = {"sql": raw, "error": str(e)}
    return {"result": result, "attempts": attempts}
