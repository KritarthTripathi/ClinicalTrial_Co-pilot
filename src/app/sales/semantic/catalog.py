"""What the model is allowed to see: governed views, metric definitions, a few worked examples."""
VIEWS = {
    "v_hcp_rx": {
        "desc": "Weekly prescriptions. One row per doctor x week x brand x plan.",
        "cols": "hcp_id, full_name, specialty, state, territory_id, decile, brand, is_ours (true for our brand Aurelis), "
                "week_start, month, plan_id, payer_name, channel, trx, nrx, nbrx"},
    "v_hcp_activity": {
        "desc": "Weekly rep activity per doctor and rep.",
        "cols": "hcp_id, full_name, specialty, territory_id, rep_id, week_start, month, calls (completed calls), "
                "vae_sent (approved emails sent), vae_opened (emails opened or clicked)"},
    "v_payer_access": {
        "desc": "Weekly claims and coverage per plan and brand.",
        "cols": "plan_id, payer_name, channel, lives, brand, is_ours, week_start, month, tier, pa_required, step_edit, "
                "submitted, paid, rejected, abandoned"},
    "v_hcp_monthly": {
        "desc": "One row per doctor per month combining prescriptions and activity.",
        "cols": "hcp_id, full_name, specialty, state, territory_id, decile, is_target, month, trx_ours, nbrx_ours, "
                "trx_all, calls, vae_sent, vae_opened"},
}
KEYWORDS = {
    "v_hcp_rx": ["prescri", "trx", "nrx", "nbrx", "new-to-brand"],
    "v_hcp_activity": ["call", "vae", "email", " rep", "reps"],
    "v_payer_access": ["payer", "plan", "formulary", "reject", "claim", "abandon", "prior auth", "tier", "coverage"],
}

import re

RANK = re.compile(r"\b(top|most|highest|lowest|fewest|least|best|worst|rank)\b", re.I)
TIME = re.compile(r"\b(last|past|recent|since|ago|latest)\b", re.I)
COND = re.compile(r"\b(more than|fewer than|less than|at least|over|under|how many)\b", re.I)
DEFS = [("reject", "Reject rate = SUM(rejected) * 1.0 / SUM(submitted)."),
        ("vae", "VAE open rate = SUM(vae_opened) * 1.0 / SUM(vae_sent)."),
        ("trx", "TRx = SUM(trx)."),
        ("nbrx", "NBRx (new-to-brand) = SUM(nbrx), not nrx."),
        ("new-to-brand", "NBRx (new-to-brand) = SUM(nbrx), not nrx."),
        ("nrx", "NRx = SUM(nrx).")]
BASE_EX = [("Total TRx for competitor brands by month",
            "SELECT month, brand, SUM(trx) AS trx FROM v_hcp_rx WHERE is_ours = false GROUP BY month, brand ORDER BY month"),
           ("Average calls per doctor by specialty",
            "SELECT specialty, SUM(calls) * 1.0 / COUNT(DISTINCT hcp_id) AS calls_per_doctor FROM v_hcp_activity GROUP BY specialty")]
RANK_EX = ("Top 5 doctors by NBRx of our brand",
           "SELECT hcp_id, SUM(nbrx) AS nbrx FROM v_hcp_rx WHERE is_ours = true GROUP BY hcp_id ORDER BY nbrx DESC LIMIT 5")
COND_EX = ("How many plans had more than 100 rejected claims?",
           "SELECT COUNT(*) FROM (SELECT plan_id FROM v_payer_access GROUP BY plan_id HAVING SUM(rejected) > 100)")


def build_prompt(question: str, views: list, data_end: str) -> str:
    q = question.lower()
    rules = ["Aggregate with SUM or COUNT and GROUP BY only the columns the question asks about."]
    if RANK.search(q):
        rules.append("For ranking questions GROUP BY only the entity (hcp_id, plan_id or rep_id), ORDER BY the aggregate DESC, "
                     "and LIMIT to the number asked (LIMIT 1 for 'the most').")
    else:
        rules.append("Do not add ORDER BY or LIMIT unless the question asks for a ranking.")
    if "our brand" in q:
        rules.append("Our brand is Aurelis: add is_ours = true, but ONLY for a view that lists an is_ours column.")
    if TIME.search(q):
        rules.append(f"The data ends with the week starting {data_end}. For 'last N weeks' use week_start > DATE '{data_end}' "
                     f"- INTERVAL (N*7) DAY. For 'last N months' GROUP BY month ORDER BY month DESC LIMIT N.")
    if COND.search(q):
        rules.append("Conditions on totals go in HAVING (inside a subquery when counting entities), never in WHERE.")
    rules.append("When listing doctors return hcp_id. Use only columns listed for the views. Return exactly ONE SELECT statement.")
    defs = []
    for kw, d in DEFS:
        if kw in q and d not in defs:
            defs.append(d)
    ex = list(BASE_EX)
    if RANK.search(q):
        ex.append(RANK_EX)
    if COND.search(q):
        ex.append(COND_EX)
    if TIME.search(q):
        ex.append(("Total calls in the last 4 weeks",
                   f"SELECT SUM(calls) FROM v_hcp_activity WHERE week_start > DATE '{data_end}' - INTERVAL 28 DAY"))
    view_text = "\n".join(f"- {v}: {VIEWS[v]['desc']} Columns: {VIEWS[v]['cols']}" for v in views)
    ex_text = "\n".join(f"Q: {a}\nSQL: {b}" for a, b in ex)
    return ("You write one DuckDB SQL query. Use ONLY these views:\n" + view_text +
            ("\nDefinitions: " + " ".join(defs) if defs else "") +
            "\nRules:\n" + "\n".join("- " + r for r in rules) +
            "\nExamples:\n" + ex_text + f"\nQ: {question}\nSQL:")
