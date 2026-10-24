"""Synthetic pharma commercial data: fictional brands, fake people. Plants known answers.
Run: python scripts/generate_pharma.py"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
OUT = Path("data/synthetic_pharma")
OUT.mkdir(parents=True, exist_ok=True)
N_HCP, N_WEEKS, PA_WEEK = 300, 52, 29          # PA_WEEK: index of the week plan P04 adds prior auth
weeks = pd.date_range("2025-01-06", periods=N_WEEKS, freq="W-MON")
widx = np.arange(N_WEEKS)

FIRST = ["Alice", "Bruno", "Chen", "Divya", "Elena", "Farid", "Grace", "Hiro", "Isabel", "Jamal",
         "Keiko", "Liam", "Mei", "Nikolai", "Olu", "Priya", "Quinn", "Rosa", "Sanjay", "Tara"]
LAST = ["Morales", "Okafor", "Lindqvist", "Sharma", "Petrov", "Nakamura", "Duarte", "Haddad", "Ivanova",
        "Kowalski", "Mbeki", "Nguyen", "Obrien", "Park", "Quispe", "Rossi", "Santos", "Tanaka", "Usman", "Varga"]
PATIENTS = ["Maria Garcia", "James Wilson", "Linda Martinez", "Robert Johnson", "Susan Clark",
            "David Lewis", "Karen Walker", "Thomas Young", "Nancy Hall", "Steven Allen"]
STATES = ["CA", "TX", "NY", "FL", "IL", "OH", "PA", "GA", "NC", "MI"]
PAYERS = ["Northstar Health", "Meridian Care", "Lakeview Plans", "Pioneer Health", "Summit Mutual", "Evergreen Health"]
CHANNELS = ["Commercial", "Medicare", "Medicaid"]
GENERIC = ["Discussed efficacy data and dosing for Aurelis. HCP receptive.",
           "Requested samples; follow-up planned in two weeks.",
           "HCP raised formulary access concerns for Medicaid patients.",
           "Reviewed new clinical data; HCP asked about long-term safety.",
           "Brief visit, office busy. Will revisit next month."]
AE = ["HCP reported a patient had a severe rash after starting Aurelis.",
      "HCP mentioned a patient hospitalized after an allergic reaction.",
      "HCP described swelling and a serious side effect in one patient."]
OFF = ["HCP asked about using Aurelis for an off-label pediatric indication.",
       "HCP interested in unapproved dosing for adolescent patients."]

# ---------------- dimensions
combo = rng.choice(len(FIRST) * len(LAST), N_HCP, replace=False)
names = [f"{FIRST[c // len(LAST)]} {LAST[c % len(LAST)]}" for c in combo]
hcp_ids = [f"H{i:04d}" for i in range(1, N_HCP + 1)]
npis = [f"SYN{2000000 + i * 7}" for i in range(N_HCP)]        # obviously fake, cannot match real NPIs
specialty = rng.choice(["Dermatology", "Rheumatology", "Primary Care"], N_HCP, p=[0.6, 0.2, 0.2])
terr = rng.integers(0, 10, N_HCP)
potential = rng.lognormal(1.0, 1.0, N_HCP)                     # heavy-tailed prescribing potential
decile = np.asarray(pd.qcut(potential, 10, labels=False)) + 1
is_target = decile >= 6
dim_hcp = pd.DataFrame({"hcp_id": hcp_ids, "npi": npis, "full_name": names, "specialty": specialty,
                        "state": [STATES[t] for t in terr], "territory_id": [f"T{t + 1:02d}" for t in terr],
                        "decile": decile, "is_target": is_target})
dim_product = pd.DataFrame({"product_id": ["PR01", "PR02", "PR03"], "brand": ["Aurelis", "Clearon", "Psorix"],
                            "is_ours": [True, False, False], "therapeutic_area": ["Dermatology"] * 3})
PIDS, MULT = ["PR01", "PR02", "PR03"], [0.7, 0.8, 0.5]
dim_payer = pd.DataFrame({"plan_id": [f"P{i + 1:02d}" for i in range(12)],
                          "payer_name": [PAYERS[i % 6] for i in range(12)],
                          "channel": [CHANNELS[i // 4] for i in range(12)],
                          "lives": rng.integers(50_000, 900_000, 12)})

# ---------------- planted behaviours
cand = np.where((decile >= 7) & ~np.isin(terr, [2, 6]))[0]
flat = rng.choice(cand, 10, replace=False)                      # many calls, no response
response = (rng.random(N_HCP) < 0.6).astype(float)
response[flat] = 0.0
rate = np.where(is_target, 0.08 + 0.025 * decile, 0.03)
rate = np.where(np.isin(terr, [2, 6]), rate * 0.2, rate)        # territories T03, T07 -> reps R03, R07 barely call
rate_mat = np.repeat(rate[:, None], N_WEEKS, axis=1)
rate_mat[flat, :] = 1.2
calls = rng.poisson(rate_mat)
vae = rng.poisson(np.repeat(np.where(is_target, 0.12, 0.04)[:, None], N_WEEKS, axis=1))
cs = np.cumsum(calls + 0.5 * vae, axis=1)
lag = np.zeros(cs.shape)
for w in range(1, N_WEEKS):                                      # touches in the previous 4 weeks
    lo = max(0, w - 4)
    lag[:, w] = cs[:, w - 1] - (cs[:, lo - 1] if lo > 0 else 0)
season = 1 + 0.15 * np.sin(2 * np.pi * widx / 52)

# ---------------- prescriptions
plan_probs = rng.dirichlet(np.ones(12) * 1.5, N_HCP)
parts = []
for h in range(N_HCP):
    for pi, (pid, mult) in enumerate(zip(PIDS, MULT)):
        lam = potential[h] * mult * 0.35 * season * (1 + (0.05 * response[h] * lag[h] if pi == 0 else 0))
        trx = rng.poisson(lam)
        plan_idx = rng.choice(12, N_WEEKS, p=plan_probs[h])
        nrx = np.minimum(rng.binomial(trx, 0.3), trx)
        nbrx = np.minimum(rng.binomial(nrx, 0.5), nrx)
        if pi == 0:                                              # plan P04 adds prior auth for our brand
            m = (plan_idx == 3) & (widx >= PA_WEEK)
            trx = np.where(m, rng.binomial(trx, 0.6), trx)
            nrx = np.minimum(nrx, trx)
            nbrx = np.minimum(np.where(m, rng.binomial(nbrx, 0.6), nbrx), nrx)
        keep = trx > 0
        parts.append(pd.DataFrame({"week_start": weeks[keep], "hcp_id": hcp_ids[h], "product_id": pid,
                                   "plan_id": [f"P{i + 1:02d}" for i in plan_idx[keep]],
                                   "nbrx": nbrx[keep], "nrx": nrx[keep], "trx": trx[keep]}))
fact_rx = pd.concat(parts, ignore_index=True)

# ---------------- activity (calls and approved emails)
rows, n = [], 0
for h in range(N_HCP):
    rep = f"R{terr[h] + 1:02d}"
    for w in range(N_WEEKS):
        for _ in range(calls[h, w]):
            n += 1
            rows.append((f"A{n:06d}", weeks[w] + pd.Timedelta(days=int(rng.integers(0, 5))), hcp_ids[h], rep,
                         "PR01", "call", "completed" if rng.random() < 0.9 else "missed", ""))
        for _ in range(vae[h, w]):
            n += 1
            rows.append((f"A{n:06d}", weeks[w] + pd.Timedelta(days=int(rng.integers(0, 5))), hcp_ids[h], rep,
                         "PR01", "vae", rng.choice(["delivered", "opened", "clicked", "bounced"], p=[.35, .45, .15, .05]), ""))
fact_activity = pd.DataFrame(rows, columns=["activity_id", "activity_date", "hcp_id", "rep_id", "product_id",
                                            "activity_type", "status", "notes_text"])
done = fact_activity.index[(fact_activity.activity_type == "call") & (fact_activity.status == "completed")].to_numpy()
fact_activity.loc[done, "notes_text"] = rng.choice(GENERIC, len(done))
pk = rng.choice(done, 35, replace=False)
ae_i, off_i, pat_i, con_i = pk[:12], pk[12:20], pk[20:30], pk[30:35]
for i in ae_i: fact_activity.at[i, "notes_text"] = str(rng.choice(AE))
for i in off_i: fact_activity.at[i, "notes_text"] = str(rng.choice(OFF))
pat_names = [PATIENTS[k % len(PATIENTS)] for k in range(len(pat_i))]
for i, p in zip(pat_i, pat_names): fact_activity.at[i, "notes_text"] = f"HCP mentioned patient {p} switched therapy last month."
phones = [f"212-555-01{k:02d}" for k in range(len(con_i))]
emails = [f"pat.contact{k}@mail.example" for k in range(len(con_i))]
for i, ph, em in zip(con_i, phones, emails): fact_activity.at[i, "notes_text"] = f"Call back at {ph} or {em}."

# ---------------- formulary and claims
frm = []
for p in dim_payer.plan_id:
    for pid in PIDS:
        tier = int(rng.choice([2, 3])) if pid == "PR01" else int(rng.integers(1, 4))
        if p == "P04" and pid == "PR01": tier = 2
        frm.append((p, pid, pd.Timestamp("2025-01-01"), tier, False, False))
frm.append(("P04", "PR01", weeks[PA_WEEK], 3, True, True))
fact_formulary = pd.DataFrame(frm, columns=["plan_id", "product_id", "effective_date", "tier", "pa_required", "step_edit"])

g = fact_rx.groupby(["week_start", "plan_id", "product_id"], as_index=False)["trx"].sum()
chan = dim_payer.set_index("plan_id")["channel"]
p_rej = 0.06 + np.where(g.plan_id.map(chan) == "Medicaid", 0.03, 0.0)
planted = ((g.plan_id == "P04") & (g.product_id == "PR01") & (g.week_start >= weeks[PA_WEEK])).to_numpy()
p_rej = np.where(planted, 0.28, p_rej)
submitted = np.ceil(g.trx.to_numpy() * 1.25).astype(int)
rejected = rng.binomial(submitted, p_rej)
fact_claims = pd.DataFrame({"week_start": g.week_start, "plan_id": g.plan_id, "product_id": g.product_id,
                            "submitted": submitted, "paid": submitted - rejected, "rejected": rejected,
                            "abandoned": rng.binomial(rejected, 0.4)})

for name, df in dict(dim_hcp=dim_hcp, dim_product=dim_product, dim_payer=dim_payer, fact_rx=fact_rx,
                     fact_activity=fact_activity, fact_formulary=fact_formulary, fact_claims=fact_claims).items():
    df.to_csv(OUT / f"{name}.csv", index=False)

truth = {"data_end": str(weeks[-1].date()), "flat_hcps": [hcp_ids[i] for i in flat],
         "low_reach_reps": ["R03", "R07"],
         "pa_plan": {"plan_id": "P04", "product_id": "PR01", "effective_date": str(weeks[PA_WEEK].date())},
         "ae_ids": fact_activity.loc[ae_i, "activity_id"].tolist(),
         "offlabel_ids": fact_activity.loc[off_i, "activity_id"].tolist(),
         "hcp_names": names, "npis": npis, "patient_names": sorted(set(pat_names)), "phones": phones, "emails": emails}
(OUT / "planted_truth.json").write_text(json.dumps(truth, indent=1))
print(f"HCPs={N_HCP} rx_rows={len(fact_rx)} activities={len(fact_activity)} claims={len(fact_claims)}")
print("planted: 10 high-call/no-response doctors, 2 low-reach reps, PA on plan P04 from", truth["pa_plan"]["effective_date"])
