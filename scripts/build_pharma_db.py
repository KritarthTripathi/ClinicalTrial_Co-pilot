"""Schema v2: load the five CSV datasets -> privacy policy -> masked DuckDB + encrypted vault. Run: python scripts/build_pharma_db.py"""
from pathlib import Path

import duckdb
import pandas as pd

from app.common.config import settings
from app.common.pii import PIIMasker
from app.common.vault import PIIVault
from app.sales.policy import apply_policy

SEM, SRC = Path("src/app/sales/semantic"), Path("data/schema_v2")
DB = Path(settings.work_dir) / "pharma.duckdb"
TABLES = ["hcp_summary_with_territory_and_tm_info", "hcp_rx_summary_report", "hcp_activity_calls_vae_suggestions",
          "territory_alignment_hierarchy", "rx_report_summary_geo"]

masker = PIIMasker()
frames = apply_policy({t: pd.read_csv(SRC / f"{t}.csv") for t in TABLES}, masker)
for df in frames.values():
    for c in df.columns:
        if c.endswith("_date"):
            df[c] = pd.to_datetime(df[c])

DB.parent.mkdir(parents=True, exist_ok=True)
if DB.exists():
    DB.unlink()
con = duckdb.connect(str(DB))
con.execute((SEM / "schema.sql").read_text())
for t, df in frames.items():
    cols = [d[0] for d in con.execute(f"SELECT * FROM {t} LIMIT 0").description]
    tmp = df[cols]
    con.register("tmp_df", tmp)
    con.execute(f"INSERT INTO {t} SELECT * FROM tmp_df")
    con.unregister("tmp_df")
con.execute((SEM / "views.sql").read_text())
PIIVault().save("pharma", masker.mapping)

for t in TABLES + ["v_hcp_rx_latest", "v_hcp_rx_trend", "v_activity_latest", "v_geo_latest", "v_geo_trend"]:
    print(f"{t:42s} {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:>7} rows")
print("pseudonymized values:", {e: sum(1 for p in masker.mapping if p.startswith(f'<{e}_')) for e in ("HCP_FULL_NAME", "TERRITORY_MANAGER_NAME", "TERRITORY_MANAGER_EMAIL")})
print("database:", DB)
