"""Parser-based SQL guard: one read-only SELECT, only approved views, always a LIMIT."""
import sqlglot
from sqlglot import exp

from app.sales.semantic.catalog import VIEWS

ALLOWED = set(VIEWS)
TIME_FUNCS = {"current_date", "current_timestamp", "current_time", "now", "today", "localtimestamp",
              "get_current_timestamp", "current_datetime"}
BAD_FUNCS = {"read_csv", "read_csv_auto", "read_parquet", "read_json", "read_text", "read_blob",
             "glob", "parquet_scan", "sniff_csv"}
WRITE_NODES = tuple(getattr(exp, n) for n in ("Insert", "Update", "Delete", "Drop", "Create", "Command", "Alter")
                    if hasattr(exp, n))


def guard(sql: str, max_rows: int = 500) -> str:
    try:
        stmts = [s for s in sqlglot.parse(sql, read="duckdb") if s is not None]
    except Exception as e:
        raise ValueError(f"could not parse SQL: {str(e)[:120]}")
    if len(stmts) != 1:
        raise ValueError("exactly one statement is allowed")
    tree = stmts[0]
    if not isinstance(tree, (exp.Select, exp.Union)):
        raise ValueError("only SELECT queries are allowed")
    if tree.find(*WRITE_NODES):
        raise ValueError("write or DDL statements are not allowed")
    for f in tree.find_all(exp.Func):
        name = f.sql_name().lower() if hasattr(f, "sql_name") else ""
        if name in BAD_FUNCS or (isinstance(f, exp.Anonymous) and str(f.name).lower() in BAD_FUNCS):
            raise ValueError("file-reading functions are not allowed")
        if name in TIME_FUNCS or (isinstance(f, exp.Anonymous) and str(f.name).lower() in TIME_FUNCS):
            raise ValueError("do not use CURRENT_DATE or NOW(); the data ends in 2025, so use the data end date from the prompt")
    ctes = {c.alias for c in tree.find_all(exp.CTE)}
    tables = {t.name for t in tree.find_all(exp.Table)}
    bad = tables - ALLOWED - ctes
    if bad:
        raise ValueError(f"tables not allowed: {sorted(bad)}. Use only: {sorted(ALLOWED)}")
    if not tree.args.get("limit"):
        tree = tree.limit(max_rows)
    return tree.sql(dialect="duckdb")
