"""Raw CSVs -> privacy policy -> masked DuckDB + encrypted vault. Run: python scripts/build_pharma_db.py"""
from pathlib import Path

import duckdb
import pandas as pd

from app.common.config import settings
from app.common.pii import PIIMasker, compliance_report
from app.common.vault import PIIVault
from app.sales.policy import apply_policy

SEM, SRC = Path("src/app/sales/semantic"), Path("data/synthetic_pharma")
DB = Path(settings.work_dir) / "pharma.duckdb"
DATES = {"fact_rx": ["week_start"], "fact_activity": ["activity_date"],
         "fact_formulary": ["effective_date"], "fact_claims": ["week_start"]}
TABLES = ["dim_hcp", "dim_product", "dim_payer", "fact_rx", "fact_activity", "fact_formulary", "fact_claims"]

masker = PIIMasker()
frames = {t: pd.read_csv(SRC / f"{t}.csv", parse_dates=DATES.get(t, [])) for t in TABLES}
frames = apply_policy(frames, masker)

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
notes = "\n".join(r[0] for r in con.execute("SELECT DISTINCT notes_text FROM fact_activity").fetchall())
rep = compliance_report(notes, masker.counts)
for t in TABLES:
    print(f"{t:15s} {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:>7} rows")
print("masked entities:", rep["masked_entities"])
print("compliance verdict on notes:", rep["verdict"], rep["reason"])
print("database:", DB)
