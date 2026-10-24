CREATE TABLE dim_hcp(hcp_id VARCHAR PRIMARY KEY, npi VARCHAR, full_name VARCHAR, specialty VARCHAR,
                     state VARCHAR, territory_id VARCHAR, decile INTEGER, is_target BOOLEAN);
CREATE TABLE dim_product(product_id VARCHAR PRIMARY KEY, brand VARCHAR, is_ours BOOLEAN, therapeutic_area VARCHAR);
CREATE TABLE dim_payer(plan_id VARCHAR PRIMARY KEY, payer_name VARCHAR, channel VARCHAR, lives INTEGER);
CREATE TABLE fact_rx(week_start DATE, hcp_id VARCHAR, product_id VARCHAR, plan_id VARCHAR,
                     nbrx INTEGER, nrx INTEGER, trx INTEGER);
CREATE TABLE fact_activity(activity_id VARCHAR, activity_date DATE, hcp_id VARCHAR, rep_id VARCHAR,
                           product_id VARCHAR, activity_type VARCHAR, status VARCHAR, notes_text VARCHAR);
CREATE TABLE fact_formulary(plan_id VARCHAR, product_id VARCHAR, effective_date DATE, tier INTEGER,
                            pa_required BOOLEAN, step_edit BOOLEAN);
CREATE TABLE fact_claims(week_start DATE, plan_id VARCHAR, product_id VARCHAR,
                         submitted INTEGER, paid INTEGER, rejected INTEGER, abandoned INTEGER);
