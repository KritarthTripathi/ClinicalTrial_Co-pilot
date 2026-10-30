"""Checks the masked schema-v2 database: row counts, no personal strings, reconciliation across levels, views."""
import re
import sys
from pathlib import Path

import pandas as pd

SRC = Path("data/schema_v2")
EXPECTED = {"hcp_summary_with_territory_and_tm_info": 500, "hcp_rx_summary_report": 6000, "hcp_activity_calls_vae_suggestions": 6456,
            "territory_alignment_hierarchy": 48, "rx_report_summary_geo": 3852}
VIEWS = {"v_hcp_rx_latest": 2000, "v_hcp_rx_trend": 2000, "v_activity_latest": 2152, "v_geo_latest": 1284, "v_geo_trend": 1284}


def main(con) -> bool:
    ok_all = True

    def check(name, cond, detail=""):
        nonlocal ok_all
        ok_all = ok_all and bool(cond)
        print(("PASS  " if cond else "FAIL  ") + name + (f"   [{detail}]" if detail else ""))

    one = lambda sql: con.execute(sql).fetchone()[0]
    for t, n in {**EXPECTED, **VIEWS}.items():
        check(f"{t} has {n} rows", one(f"SELECT COUNT(*) FROM {t}") == n, str(one(f"SELECT COUNT(*) FROM {t}")))
    # no real HCP names, manager names or emails anywhere in the database
    originals = set()
    for t, cols in {"hcp_summary_with_territory_and_tm_info": ["hcp_full_name", "territory_manager_name", "territory_manager_email"],
                    "territory_alignment_hierarchy": ["territory_manager_name", "territory_manager_email"]}.items():
        for c in cols:
            originals |= set(pd.read_csv(SRC / f"{t}.csv")[c].astype(str))
    blob = " ".join(r[0] for t, c in (("hcp_summary_with_territory_and_tm_info", "hcp_full_name"), ("hcp_summary_with_territory_and_tm_info", "territory_manager_name"),
                                      ("hcp_summary_with_territory_and_tm_info", "territory_manager_email"), ("hcp_rx_summary_report", "hcp_full_name"),
                                      ("hcp_activity_calls_vae_suggestions", "hcp_full_name"), ("territory_alignment_hierarchy", "territory_manager_name"),
                                      ("territory_alignment_hierarchy", "territory_manager_email"))
                    for r in con.execute(f"SELECT DISTINCT {c} FROM {t}").fetchall())
    leaks = [o for o in originals if o in blob]
    check("no real HCP name, manager name or email in the database", not leaks, f"{len(originals)} checked, {len(leaks)} leaked")
    names = [r[0] for r in con.execute("SELECT DISTINCT hcp_full_name FROM hcp_rx_summary_report").fetchall()]
    check("hcp_full_name holds codes like <HCP_FULL_NAME_n>", all(re.fullmatch(r"<HCP_FULL_NAME_\d+>", n) for n in names))
    # reconciliation: every geo level adds up to the HCP-level total (latest period, per grain)
    for g in ("W", "4W", "M", "13W"):
        total = one(f"SELECT SUM(trx) FROM v_hcp_rx_latest WHERE grain_code = '{g}'")
        for lvl in ("TERRITORY", "DISTRICT", "AREA", "DIVISION"):
            check(f"geo {lvl} {g} total equals HCP total", one(f"SELECT SUM(trx) FROM v_geo_latest WHERE geo_level = '{lvl}' AND grain_code = '{g}'") == total)
    check("every HCP territory exists in the alignment table", one("SELECT COUNT(DISTINCT territory_name) FROM hcp_summary_with_territory_and_tm_info WHERE territory_name NOT IN (SELECT territory_name FROM territory_alignment_hierarchy)") == 0)
    check("latest period ends 2026-01-29 for every grain", one("SELECT COUNT(DISTINCT grain_end_date) FROM v_hcp_rx_latest") == 1 and str(one("SELECT MAX(grain_end_date) FROM v_hcp_rx_latest"))[:10] == "2026-01-29")
    check("trend views have a previous value for every latest row", one("SELECT COUNT(*) FROM v_hcp_rx_trend WHERE previous_trx IS NULL") == 0)
    print("\nALL CHECKS PASSED" if ok_all else "\nSOME CHECKS FAILED")
    return ok_all


if __name__ == "__main__":
    import duckdb
    from app.common.config import settings
    sys.exit(0 if main(duckdb.connect(str(Path(settings.work_dir) / "pharma.duckdb"), read_only=True)) else 1)
