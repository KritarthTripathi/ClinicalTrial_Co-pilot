"""Routing accuracy for the supervisor and the sales router.
Run: python -m app.agents.route_eval --file data/evals/routing_holdout.yaml --mode rules|fast|hybrid|llm
Modes: rules = no LLM; fast = LLM only when the rules are unsure; hybrid = LLM always decides, rules can override; llm = LLM only."""
import argparse
import json
import re
import time
from collections import Counter
from pathlib import Path

import yaml

from app.agents.llm_router import sales_router_llm, supervisor_llm
from app.agents.routing import route_level
from app.common.qmask import mask_question
from app.common.vault import PIIVault
from app.sales.nodes.agent import connect, load_known


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="data/evals/routing_holdout.yaml")
    ap.add_argument("--mode", default="hybrid", choices=["rules", "fast", "hybrid", "llm"])
    a = ap.parse_args()
    con = connect()
    known = load_known(con)
    con.close()
    mapping = PIIVault().load("pharma")
    qs = yaml.safe_load(Path(a.file).read_text())
    rows, methods = [], Counter()
    for q in qs:
        t0 = time.time()
        mq = mask_question(q["question"], mapping)
        sup = route_level("supervisor", mq, known, supervisor_llm, a.mode)
        sal = route_level("sales", mq, known, sales_router_llm, a.mode) if (sup["final"] == "sales") else None
        methods[sup["method"]] += 1
        if sal:
            methods[sal["method"]] += 1
        sup_ok = sup["final"] == q["route"]
        agent_ok = None if q["route"] != "sales" else bool(sal and sal["final"] == q.get("agent"))
        ok = sup_ok and (agent_ok is not False)
        rows.append({"question": q["question"][:90], "expected": q.get("agent", q["route"]), "supervisor": sup["final"], "sales": sal["final"] if sal else None,
                     "ok": ok, "clarify": "clarify" in (sup["final"], sal["final"] if sal else ""), "seconds": round(time.time() - t0, 1)})
        if not ok:
            print(f"MISS  expected {rows[-1]['expected']:<15} got {rows[-1]['supervisor']}/{rows[-1]['sales']}  {rows[-1]['question']}")
    n = len(rows)
    s_ok = sum(r["supervisor"] == ("sales" if r["expected"].startswith("sales") else r["expected"]) for r in rows)
    sales_rows = [r for r in rows if r["expected"].startswith("sales")]
    a_ok = sum(r["sales"] == r["expected"] for r in sales_rows)
    print(f"\n[{a.mode}] supervisor route correct: {s_ok}/{n} ({s_ok / n:.0%})")
    print(f"[{a.mode}] sales agent correct: {a_ok}/{len(sales_rows)} ({a_ok / max(len(sales_rows), 1):.0%})")
    print(f"[{a.mode}] fully correct routing: {sum(r['ok'] for r in rows)}/{n}   clarify answers: {sum(r['clarify'] for r in rows)}   methods: {dict(methods)}")
    out = f"data/evals/route_{Path(a.file).stem}_{a.mode}.json"
    json.dump({"mode": a.mode, "correct": sum(r["ok"] for r in rows), "n": n, "methods": dict(methods), "rows": rows}, open(out, "w"), indent=1)
    print("saved", out)


if __name__ == "__main__":
    main()
