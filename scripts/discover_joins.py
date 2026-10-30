"""Automatic join discovery for the schema-v2 tables (pandas only; runs anywhere).
For every pair of tables it tests candidate join keys and keeps only joins that cannot silently multiply rows.
Output: src/app/sales/semantic/joins.yml (machine use) and docs/JOINS.md (for you to review and approve).
Run from the project root:  python scripts/discover_joins.py"""
from itertools import combinations
from pathlib import Path

import pandas as pd
import yaml

SRC = Path("data/schema_v2")
OUT_YML = Path("src/app/sales/semantic/joins.yml")
OUT_MD = Path("docs/JOINS.md")
TABLES = ["hcp_summary_with_territory_and_tm_info", "hcp_rx_summary_report", "hcp_activity_calls_vae_suggestions",
          "territory_alignment_hierarchy", "rx_report_summary_geo"]
# columns that can act as join keys. Names, emails and addresses are attributes, not keys; low-cardinality columns
# (division, area, grain, type) are never keys but are used as CONTEXT (queries always filter on them).
KEY_CANDIDATES = ["hcp_ref_id", "territory_name", "district_name", "product_name"]
CONTEXT = ["grain_code", "grain_end_date", "activity_type", "geo_level"]
MIN_MATCH = 0.99

df = {t: pd.read_csv(SRC / f"{t}.csv") for t in TABLES}
meta = {}
for t, d in df.items():
    metrics = [c for c in d.columns if pd.api.types.is_integer_dtype(d[c]) and c not in ("decile",)]
    ctx = [c for c in CONTEXT if c in d.columns]
    cand = [c for c in d.columns if c not in metrics and not c.startswith(("grain_start", "previous_")) and not c.startswith(("hcp_full", "territory_manager", "address", "city", "state"))]
    key = None
    for k in range(1, len(cand) + 1):
        for sub in combinations(cand, k):
            if d.groupby(list(sub)).size().max() == 1:
                key = list(sub)
                break
        if key:
            break
    meta[t] = {"natural_key": key, "context": ctx, "metrics": metrics, "rows": len(d)}


def max_rows_per_key(t, J):
    return int(df[t].groupby(J + meta[t]["context"]).size().max())


def unmatched_values(many, one, J):
    keys = df[one][J].drop_duplicates()
    m = df[many].merge(keys, on=J, how="left", indicator=True)
    return m[m._merge == "left_only"][J], (m._merge == "both").mean()


joins, rejected = [], []
for a, b in combinations(TABLES, 2):
    shared = [c for c in KEY_CANDIDATES if c in df[a].columns and c in df[b].columns]
    accepted = []
    for size in (1, 2):
        for J in combinations(shared, size):
            J = list(J)
            if any(set(x) < set(J) for x in accepted):
                continue                                           # keep minimal keys only
            ua, ub = max_rows_per_key(a, J) == 1, max_rows_per_key(b, J) == 1
            if not ua and not ub:
                if size == 1:
                    rejected.append({"tables": [a, b], "on": J, "reason": "many_to_many",
                                     "suggestion": "do not join; filter with  IN (SELECT ... )  or reduce one side to one row per key first"})
                continue
            one, many = (a, b) if ua else (b, a)
            card = "one_to_one" if (ua and ub) else "one_to_many"
            miss, rate = unmatched_values(many, one, J)
            note, req = "", None
            if rate < MIN_MATCH:
                vals = set(map(tuple, miss.values.tolist()))
                if vals <= {("ALL",) * len(J)}:
                    ok_rows = df[many].merge(df[one][J].drop_duplicates(), on=J)
                    req = (f"geo_level IN ({', '.join(repr(x) for x in sorted(ok_rows.geo_level.unique()))})" if "geo_level" in ok_rows.columns else None)
                    note = f"rows with 'ALL' do not match; only {req or 'the matching rows'} can be joined"
                else:
                    continue                                       # poor overlap: not a real key
            has_metrics = bool(meta[one]["metrics"])
            safe_as = "semi_join" if (has_metrics and card != "one_to_one") else "join"
            if safe_as == "semi_join":
                note = (note + " " if note else "") + f"{one} holds numbers that would be counted several times after a JOIN; use  WHERE key IN (SELECT key FROM ...)  instead."
            if meta[one]["context"] or meta[many]["context"]:
                ctx = sorted(set(meta[one]["context"] + meta[many]["context"]))
                note = (note + " " if note else "") + f"Unique only within one {'/'.join(ctx)}: filter these (the *_latest views already hold one period)."
            example = (f"{one} WHERE {', '.join(J)} IN (SELECT {', '.join(J)} FROM {many} WHERE <filter>)" if safe_as == "semi_join" else
                       f"{one} a JOIN {many} b ON " + " AND ".join(f"a.{c} = b.{c}" for c in J))
            one_cov = float(df[one][J].drop_duplicates().merge(df[many][J].drop_duplicates(), on=J, how="inner").shape[0] / df[one][J].drop_duplicates().shape[0])
            joins.append({"id": f"J{len(joins) + 1:02d}", "one": one, "many": many, "on": J, "cardinality": card, "safe_as": safe_as,
                          "many_side_match_rate": round(float(rate), 3), "one_side_coverage": round(one_cov, 3),
                          "requires_filter": req, "pattern": example, "note": note, "approved": True})
            accepted.append(J)

OVR = Path("src/app/sales/semantic/joins_overrides.yml")
disabled = (yaml.safe_load(OVR.read_text()) or {}).get("disabled", []) if OVR.exists() else []
removed = [j for j in joins if any(j["one"] == d["one"] and j["many"] == d["many"] and j["on"] == d["columns"] for d in disabled)]
joins = [j for j in joins if j not in removed]
for i, j in enumerate(joins, 1):
    j["id"] = f"J{i:02d}"
OUT_YML.parent.mkdir(parents=True, exist_ok=True)
OUT_YML.write_text("# Proposed by scripts/discover_joins.py. Set approved: false to disable a join. Agents use only approved joins.\n" +
                   yaml.safe_dump({"version": 1, "tables": meta, "joins": joins, "removed_by_owner": [{k: r[k] for k in ("one", "many", "on")} for r in removed], "rejected": rejected}, sort_keys=False, width=200))
L = ["# Join discovery report\n", "Generated by `scripts/discover_joins.py`. Review, then edit `approved` in `joins.yml`.\n", "## Tables\n",
     "| Table | Rows | Natural key (unique) | Context filters | Metric columns |", "|---|---|---|---|---|"]
for t, m in meta.items():
    L.append(f"| {t} | {m['rows']} | {', '.join(m['natural_key'] or [])} | {', '.join(m['context'])} | {', '.join(m['metrics']) or '-'} |")
L += ["\n## Safe joins (proposed)\n", "| ID | One side | Many side | ON | Cardinality | Use as | Match rate | Pattern | Notes |", "|---|---|---|---|---|---|---|---|---|"]
for j in joins:
    L.append(f"| {j['id']} | {j['one']} | {j['many']} | {', '.join(j['on'])} | {j['cardinality']} | **{j['safe_as']}** | {j['many_side_match_rate']:.0%} | `{j['pattern']}` | {j['note']} |")
L += ["\n## Removed by owner\n"] + [f"- {r['one']} to {r['many']} on {', '.join(r['on'])}" for r in removed] + ["\n## Rejected (would multiply rows)\n", "| Tables | ON | Why |", "|---|---|---|"]
for r in rejected:
    L.append(f"| {r['tables'][0]} + {r['tables'][1]} | {', '.join(r['on'])} | {r['reason']}: {r['suggestion']} |")
OUT_MD.write_text("\n".join(L) + "\n")
print(f"{len(joins)} safe joins, {len(rejected)} rejected -> {OUT_YML}, {OUT_MD}")
for t, m in meta.items():
    print(f"  {t}: key={m['natural_key']} context={m['context']} metrics={m['metrics']}")
for j in joins:
    print(f"  {j['id']} {j['one']} (one) -> {j['many']} (many) ON {j['on']} {j['cardinality']} use as {j['safe_as']}, match {j['many_side_match_rate']:.0%}" + (f", needs {j['requires_filter']}" if j['requires_filter'] else ""))
for r in rejected:
    print(f"  REJECT {r['tables'][0]} + {r['tables'][1]} ON {r['on']}")
