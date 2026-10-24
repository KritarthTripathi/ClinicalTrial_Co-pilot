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
METRICS_TEXT = ("TRx = SUM(trx). NRx = SUM(nrx). NBRx = SUM(nbrx). Reject rate = SUM(rejected)*1.0/SUM(submitted). "
                "VAE open rate = SUM(vae_opened)*1.0/SUM(vae_sent). Our brand is Aurelis.")
EXAMPLES = """Q: Total TRx for competitor brands by month
SQL: SELECT month, brand, SUM(trx) AS trx FROM v_hcp_rx WHERE is_ours = false GROUP BY month, brand ORDER BY month
Q: Average calls per doctor by specialty
SQL: SELECT specialty, SUM(calls) * 1.0 / COUNT(DISTINCT hcp_id) AS calls_per_doctor FROM v_hcp_activity GROUP BY specialty
Q: Top 5 doctors by NBRx of our brand
SQL: SELECT hcp_id, SUM(nbrx) AS nbrx FROM v_hcp_rx WHERE is_ours = true GROUP BY hcp_id ORDER BY nbrx DESC LIMIT 5
Q: Which 2 plans submitted the most claims?
SQL: SELECT plan_id, SUM(submitted) AS submitted FROM v_payer_access GROUP BY plan_id ORDER BY submitted DESC LIMIT 2"""
TEMPLATE = """You write one DuckDB SQL query. Use ONLY these views and ONLY the columns listed for them:
{views}
Definitions: {metrics}
Rules:
- Always aggregate with SUM or COUNT and GROUP BY only what the question asks about (top doctors: group by hcp_id only; plans: plan_id only; reps: rep_id only), then ORDER BY the aggregate DESC and LIMIT N.
- Filter on is_ours = true only if the question says "our brand" and the view has an is_ours column.
- Add a date filter only if the question mentions a time period. The data ends with the week starting {data_end}; for "last N weeks" use week_start > DATE '{data_end}' - INTERVAL (N*7) DAY.
- When listing doctors return hcp_id. Return exactly ONE SELECT statement and nothing else.
Examples:
{examples}
Q: {question}
SQL:"""
