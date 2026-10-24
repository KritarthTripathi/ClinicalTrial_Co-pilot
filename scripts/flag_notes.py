"""Rule-based compliance flags for call notes (simulated policy). Reports counts and ids, not note text."""
import json
import re
from pathlib import Path

import duckdb

from app.common.config import settings

t = json.load(open("data/synthetic_pharma/planted_truth.json"))
con = duckdb.connect(str(Path(settings.work_dir) / "pharma.duckdb"), read_only=True)
RULES = {"possible_adverse_event": r"severe|rash|adverse|side effect|hospital|allergic|swelling",
         "possible_off_label": r"off-label|off label|unapproved",
         "patient_identifier_masked": r"<PERSON_\d+>"}
flags = {k: [] for k in RULES}
for aid, note in con.execute("SELECT activity_id, notes_text FROM fact_activity WHERE notes_text <> ''").fetchall():
    for k, rx in RULES.items():
        if re.search(rx, note, re.I):
            flags[k].append(aid)


def score(found, truth):
    f, tr = set(found), set(truth)
    return round(len(f & tr) / max(len(tr), 1), 3), round(len(f & tr) / max(len(f), 1), 3)


for k, ids in flags.items():
    print(f"{k:28s} flagged {len(ids)}")
print("adverse-event recall/precision:", score(flags["possible_adverse_event"], t["ae_ids"]))
print("off-label recall/precision:    ", score(flags["possible_off_label"], t["offlabel_ids"]))
Path("data/evals").mkdir(parents=True, exist_ok=True)
json.dump({k: len(v) for k, v in flags.items()}, open("data/evals/notes_flags.json", "w"), indent=1)
