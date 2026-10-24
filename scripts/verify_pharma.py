"""Checks the masked database: no planted private strings, and planted stories are findable."""
import json
import sys
from pathlib import Path

import duckdb

from app.common.config import settings

t = json.load(open("data/synthetic_pharma/planted_truth.json"))
con = duckdb.connect(str(Path(settings.work_dir) / "pharma.duckdb"), read_only=True)
ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and bool(cond)
    print(("PASS  " if cond else "FAIL  ") + name + (f"   [{detail}]" if detail else ""))


for tbl in ["dim_hcp", "fact_rx", "fact_activity", "fact_claims", "fact_formulary"]:
    n = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    check(f"{tbl} has rows", n > 0, str(n))

blob = " ".join(r[0] for q in ("SELECT full_name FROM dim_hcp", "SELECT npi FROM dim_hcp",
                               "SELECT notes_text FROM fact_activity") for r in con.execute(q).fetchall())
planted = t["hcp_names"] + t["npis"] + t["patient_names"] + t["phones"] + t["emails"]
leaks = [p for p in planted if p in blob]
check("no planted private strings in the database", not leaks, f"{len(planted)} planted, {len(leaks)} leaked: {leaks[:5]}")

top = {r[0] for r in con.execute("SELECT hcp_id FROM v_hcp_activity GROUP BY hcp_id ORDER BY SUM(calls) DESC LIMIT 10").fetchall()}
check("10 planted high-call doctors are the top 10 by calls", set(t["flat_hcps"]) == top)
low = {r[0] for r in con.execute("SELECT rep_id FROM v_hcp_activity GROUP BY rep_id ORDER BY SUM(calls) ASC LIMIT 2").fetchall()}
check("2 planted low-reach reps have the fewest calls", low == set(t["low_reach_reps"]), str(sorted(low)))

eff = t["pa_plan"]["effective_date"]
rr = con.execute(f"""SELECT SUM(CASE WHEN week_start < DATE '{eff}' THEN rejected END) * 1.0 / SUM(CASE WHEN week_start < DATE '{eff}' THEN submitted END),
                            SUM(CASE WHEN week_start >= DATE '{eff}' THEN rejected END) * 1.0 / SUM(CASE WHEN week_start >= DATE '{eff}' THEN submitted END)
                     FROM v_payer_access WHERE plan_id = 'P04' AND is_ours""").fetchone()
check("plan P04 reject rate jumps after prior authorization", rr[0] < 0.12 and rr[1] > 0.2, f"before {rr[0]:.3f}, after {rr[1]:.3f}")
pa = con.execute("SELECT MAX(CASE WHEN pa_required THEN 1 ELSE 0 END) FROM v_payer_access WHERE plan_id = 'P04' AND is_ours").fetchone()[0]
check("formulary view shows PA on plan P04", pa == 1)
print("\nALL CHECKS PASSED" if ok else "\nSOME CHECKS FAILED")
sys.exit(0 if ok else 1)
