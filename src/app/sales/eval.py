"""Execution-accuracy evaluation. Run: python -m app.sales.eval [--file ...] [--agent geo|hcp|activity] [--e2e | --single]
  default   each question goes straight to its own agent (measures SQL accuracy per agent)
  --e2e     through supervisor and sales router (routing mistakes count as failures)
  --single  every question to one agent with all tables (the earlier single-agent design, for comparison)
Questions are masked like real use; reference SQL may contain {mask:Real Name} tokens, replaced by the database codes."""
import argparse
import json
import os
import re
import time
from collections import defaultdict
from pathlib import Path

import yaml

from app.common.qmask import mask_question
from app.common.tracing import init_tracing
from app.common.vault import PIIVault
from app.sales.graph import run_sales_agent
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


def relaxed(mode, got, ref):
    """Like same(), but extra columns in the answer are tolerated (for example an echoed filter column)."""
    if mode != "rows_set":
        return same(mode, got, ref)
    if len(got) != len(ref):
        return False
    used = set()
    for r in ref:
        want = {nv(v) for v in r}
        for i, g in enumerate(got):
            if i not in used and want <= {nv(v) for v in g}:
                used.add(i)
                break
        else:
            return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--file", default=str(GOLDEN))
    ap.add_argument("--agent", choices=["geo", "hcp", "activity"])
    ap.add_argument("--e2e", action="store_true")
    ap.add_argument("--single", action="store_true")
    ap.add_argument("--no-trace", action="store_true")
    a = ap.parse_args()
    if not a.no_trace:
        init_tracing()
    mode = "e2e" if a.e2e else "single" if a.single else "direct"
    mapping = PIIVault().load("pharma")
    rev = {orig: ph for ph, orig in mapping.items()}
    qs = yaml.safe_load(Path(a.file).read_text())
    if a.agent:
        qs = [q for q in qs if q.get("agent") == f"sales_{a.agent}"]
    qs = qs[: a.limit] if a.limit else qs
    if mode == "e2e":
        from app.agents.hierarchy import run_question
    con, results = connect(), []
    for q in qs:
        t0 = time.time()
        masked = mask_question(q["question"], mapping)
        if mode == "e2e":
            st = run_question(masked, skip_narrate=True, checkpoint=False)
            err = "" if st.get("status") == "answered" else f"{st.get('status')}: {str(st.get('answer', ''))[:120]}"
            routed = st.get("agent")
        else:
            st = run_sales_agent("sales_all" if mode == "single" else q.get("agent", "sales_all"), masked, True)
            err, routed = st.get("error", ""), q.get("agent")
        ref_sql = re.sub(r"\{mask:([^}]+)\}", lambda m: rev[m.group(1)], q["reference_sql"])
        ref = con.execute(ref_sql).fetchall()
        got = st.get("rows", [])
        ok = (not err) and same(q["compare"], got, ref)
        ok2 = (not err) and relaxed(q["compare"], got, ref)
        results.append({"id": q["id"], "agent": q.get("agent"), "routed_to": routed, "ok": ok, "relaxed_ok": ok2, "attempts": st.get("attempts"),
                        "seconds": round(time.time() - t0, 1), "sql": st.get("sql") or st.get("sql_raw"), "error": err})
        print(f"{'PASS' if ok else 'FAIL'}  {q['id']}  {results[-1]['seconds']}s  {str(q.get('agent'))[6:]:<8} -> {str(routed)[6:]:<8} {masked[:48]}")
    n = len(results)
    acc, acc2 = sum(r["ok"] for r in results) / n, sum(r["relaxed_ok"] for r in results) / n
    print(f"\n[{mode}] Execution accuracy: {acc:.0%} ({sum(r['ok'] for r in results)}/{n})")
    print(f"[{mode}] Relaxed accuracy (extra columns tolerated): {acc2:.0%} ({sum(r['relaxed_ok'] for r in results)}/{n})")
    by = defaultdict(list)
    for r in results:
        by[r["agent"]].append(r["ok"])
    print("per agent:", {k: f"{sum(v)}/{len(v)}" for k, v in by.items()})
    if mode == "e2e":
        print(f"routing correct: {sum(r['routed_to'] == r['agent'] for r in results)}/{n}")
    for r in results:
        if not r["ok"]:
            print(f"\n{r['id']} generated: {str(r['sql'])[:300]}\n   error: {r['error']}")
    stem = Path(a.file).stem
    out = f"data/evals/last_run_{stem}_{mode}_{os.getenv('PROMPT_MODE', 'full')}.json"
    json.dump({"mode": mode, "prompt_mode": os.getenv("PROMPT_MODE", "full"), "router_mode": os.getenv("ROUTER_MODE", "hybrid"),
               "accuracy": acc, "relaxed_accuracy": acc2, "results": results}, open(out, "w"), indent=1)
    print("saved", out)


if __name__ == "__main__":
    main()
