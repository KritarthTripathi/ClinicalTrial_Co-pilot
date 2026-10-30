CREATE TABLE hcp_summary_with_territory_and_tm_info(
  hcp_ref_id VARCHAR, hcp_full_name VARCHAR, address_line VARCHAR, city VARCHAR, state VARCHAR,
  territory_name VARCHAR, district_name VARCHAR, area_name VARCHAR, division_name VARCHAR,
  territory_manager_name VARCHAR, territory_manager_email VARCHAR, product_name VARCHAR);
CREATE TABLE hcp_rx_summary_report(
  hcp_ref_id VARCHAR, hcp_full_name VARCHAR, territory_name VARCHAR, district_name VARCHAR, area_name VARCHAR,
  division_name VARCHAR, product_name VARCHAR, trx INTEGER, nbrx INTEGER, nts INTEGER, grain_code VARCHAR,
  grain_start_date DATE, grain_end_date DATE, previous_start_date DATE, previous_end_date DATE);
CREATE TABLE hcp_activity_calls_vae_suggestions(
  hcp_ref_id VARCHAR, hcp_full_name VARCHAR, territory_name VARCHAR, district_name VARCHAR, area_name VARCHAR,
  division_name VARCHAR, activity_type VARCHAR, suggested_engagements INTEGER, activity_count INTEGER, grain_code VARCHAR,
  grain_start_date DATE, grain_end_date DATE, previous_start_date DATE, previous_end_date DATE);
CREATE TABLE territory_alignment_hierarchy(
  area_name VARCHAR, district_name VARCHAR, territory_name VARCHAR, division_name VARCHAR, state VARCHAR,
  territory_manager_name VARCHAR, territory_manager_email VARCHAR);
CREATE TABLE rx_report_summary_geo(
  geo_level VARCHAR, area_name VARCHAR, district_name VARCHAR, territory_name VARCHAR, division_name VARCHAR,
  product_name VARCHAR, trx INTEGER, nbrx INTEGER, nts INTEGER, grain_code VARCHAR,
  grain_start_date DATE, grain_end_date DATE, previous_start_date DATE, previous_end_date DATE);
