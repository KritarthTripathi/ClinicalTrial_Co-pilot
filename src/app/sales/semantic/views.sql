CREATE OR REPLACE VIEW v_hcp_rx AS
SELECT r.hcp_id, h.full_name, h.specialty, h.state, h.territory_id, h.decile,
       p.brand, p.is_ours, r.week_start, CAST(date_trunc('month', r.week_start) AS DATE) AS month,
       r.plan_id, pl.payer_name, pl.channel, r.trx, r.nrx, r.nbrx
FROM fact_rx r
JOIN dim_hcp h ON h.hcp_id = r.hcp_id
JOIN dim_product p ON p.product_id = r.product_id
LEFT JOIN dim_payer pl ON pl.plan_id = r.plan_id;

CREATE OR REPLACE VIEW v_hcp_activity AS
SELECT a.hcp_id, h.full_name, h.specialty, h.territory_id, a.rep_id,
       CAST(date_trunc('week', a.activity_date) AS DATE) AS week_start,
       CAST(date_trunc('month', a.activity_date) AS DATE) AS month,
       SUM(CASE WHEN a.activity_type = 'call' AND a.status = 'completed' THEN 1 ELSE 0 END) AS calls,
       SUM(CASE WHEN a.activity_type = 'vae' THEN 1 ELSE 0 END) AS vae_sent,
       SUM(CASE WHEN a.activity_type = 'vae' AND a.status IN ('opened', 'clicked') THEN 1 ELSE 0 END) AS vae_opened
FROM fact_activity a
JOIN dim_hcp h ON h.hcp_id = a.hcp_id
GROUP BY ALL;

CREATE OR REPLACE VIEW v_payer_access AS
SELECT c.plan_id, pl.payer_name, pl.channel, pl.lives, p.brand, p.is_ours,
       c.week_start, CAST(date_trunc('month', c.week_start) AS DATE) AS month,
       f.tier, f.pa_required, f.step_edit, c.submitted, c.paid, c.rejected, c.abandoned
FROM fact_claims c
JOIN dim_payer pl ON pl.plan_id = c.plan_id
JOIN dim_product p ON p.product_id = c.product_id
ASOF LEFT JOIN fact_formulary f
  ON f.plan_id = c.plan_id AND f.product_id = c.product_id AND c.week_start >= f.effective_date;

CREATE OR REPLACE VIEW v_hcp_monthly AS
WITH rx AS (
  SELECT hcp_id, month, SUM(CASE WHEN is_ours THEN trx ELSE 0 END) AS trx_ours,
         SUM(CASE WHEN is_ours THEN nbrx ELSE 0 END) AS nbrx_ours, SUM(trx) AS trx_all
  FROM v_hcp_rx GROUP BY hcp_id, month),
act AS (
  SELECT hcp_id, month, SUM(calls) AS calls, SUM(vae_sent) AS vae_sent, SUM(vae_opened) AS vae_opened
  FROM v_hcp_activity GROUP BY hcp_id, month)
SELECT h.hcp_id, h.full_name, h.specialty, h.state, h.territory_id, h.decile, h.is_target, rx.month,
       rx.trx_ours, rx.nbrx_ours, rx.trx_all,
       COALESCE(act.calls, 0) AS calls, COALESCE(act.vae_sent, 0) AS vae_sent,
       COALESCE(act.vae_opened, 0) AS vae_opened
FROM dim_hcp h
JOIN rx ON rx.hcp_id = h.hcp_id
LEFT JOIN act ON act.hcp_id = rx.hcp_id AND act.month = rx.month;
