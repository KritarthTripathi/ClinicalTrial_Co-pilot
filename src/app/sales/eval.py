"""Execution-accuracy evaluation. Run: python -m app.sales.eval [--limit N]"""
import argparse
import json
import time
import uuid
from pathlib import Path

import yaml

from app.common.tracing import init_tracing
from app.sales.graph import build_graph
from app.sales.nodes.agent import connect

GOLDEN = Path("data/evals/sales_golden.yaml")


def nv(v):
    return str(round(float(v), 2)) if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v)


def same(mode, got, ref):
    try:
        if mode == "scalar":
            return abs(float(got[0][0]) - float(ref[0][0])) < 0.01
        if mode == "first_col_set":
            return {nv(r[0]) for r in got} == {nv(r[0]) for r in ref}
        return {tuple(sorted(nv(v) for v in r)) for r in got} == {tuple(sorted(nv(v) for v in r)) for r in ref}
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--no-trace", action="store_true")
    a = ap.parse_args()
    if not a.no_trace:
        init_tracing()
    qs = yaml.safe_load(GOLDEN.read_text())
    qs = qs[: a.limit] if a.limit else qs
    app, con, results = build_graph(), connect(), []
    for q in qs:
        t0 = time.time()
        st = app.invoke({"question": q["question"], "skip_narrate": True, "attempts": 0},
                        config={"configurable": {"thread_id": uuid.uuid4().hex}})
        ref = con.execute(q["reference_sql"]).fetchall()
        ok = (not st.get("error")) and same(q["compare"], st.get("rows", []), ref)
        results.append({"id": q["id"], "ok": ok, "attempts": st.get("attempts"), "seconds": round(time.time() - t0, 1),
                        "sql": st.get("sql") or st.get("sql_raw"), "error": st.get("error", "")})
        print(f"{'PASS' if ok else 'FAIL'}  {q['id']}  {results[-1]['seconds']}s  attempts={st.get('attempts')}  {q['question'][:60]}")
    acc = sum(r["ok"] for r in results) / len(results)
    print(f"\nExecution accuracy: {acc:.0%} ({sum(r['ok'] for r in results)}/{len(results)})")
    for r in results:
        if not r["ok"]:
            print(f"\n{r['id']} generated: {str(r['sql'])[:300]}\n   error: {r['error']}")
    json.dump({"accuracy": acc, "results": results}, open("data/evals/last_run.json", "w"), indent=1)


if __name__ == "__main__":
    main()
