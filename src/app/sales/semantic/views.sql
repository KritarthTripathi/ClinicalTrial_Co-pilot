-- "latest" views keep only the most recent period of each grain_code, so the model never has to write MAX(date) subqueries.
-- "trend" views put the previous period's numbers next to the latest ones (joined on the previous_* dates).
DROP VIEW IF EXISTS v_hcp_rx_trend;
DROP VIEW IF EXISTS v_geo_trend;
DROP VIEW IF EXISTS v_hcp_rx_latest;
DROP VIEW IF EXISTS v_activity_latest;
DROP VIEW IF EXISTS v_geo_latest;

CREATE VIEW v_hcp_rx_latest AS
SELECT r.* FROM hcp_rx_summary_report r
WHERE r.grain_end_date = (SELECT MAX(x.grain_end_date) FROM hcp_rx_summary_report x WHERE x.grain_code = r.grain_code);

CREATE VIEW v_activity_latest AS
SELECT a.* FROM hcp_activity_calls_vae_suggestions a
WHERE a.grain_end_date = (SELECT MAX(x.grain_end_date) FROM hcp_activity_calls_vae_suggestions x WHERE x.grain_code = a.grain_code);

CREATE VIEW v_geo_latest AS
SELECT g.* FROM rx_report_summary_geo g
WHERE g.grain_end_date = (SELECT MAX(x.grain_end_date) FROM rx_report_summary_geo x WHERE x.grain_code = g.grain_code);

CREATE VIEW v_hcp_rx_trend AS
SELECT c.hcp_ref_id, c.hcp_full_name, c.territory_name, c.district_name, c.area_name, c.division_name, c.product_name,
       c.grain_code, c.grain_start_date, c.grain_end_date, c.trx, c.nbrx, c.nts,
       p.trx AS previous_trx, p.nbrx AS previous_nbrx, p.nts AS previous_nts,
       c.trx - p.trx AS trx_change,
       CASE WHEN p.trx > 0 THEN (c.trx - p.trx) * 100.0 / p.trx END AS trx_change_pct
FROM v_hcp_rx_latest c
JOIN hcp_rx_summary_report p
  ON p.hcp_ref_id = c.hcp_ref_id AND p.product_name = c.product_name AND p.grain_code = c.grain_code
 AND p.grain_start_date = c.previous_start_date AND p.grain_end_date = c.previous_end_date;

CREATE VIEW v_geo_trend AS
SELECT c.geo_level, c.area_name, c.district_name, c.territory_name, c.division_name, c.product_name,
       c.grain_code, c.grain_start_date, c.grain_end_date, c.trx, c.nbrx, c.nts,
       p.trx AS previous_trx, p.nbrx AS previous_nbrx, p.nts AS previous_nts
FROM v_geo_latest c
JOIN rx_report_summary_geo p
  ON p.geo_level = c.geo_level AND p.area_name = c.area_name AND p.district_name = c.district_name
 AND p.territory_name = c.territory_name AND p.division_name = c.division_name AND p.product_name = c.product_name
 AND p.grain_code = c.grain_code AND p.grain_start_date = c.previous_start_date AND p.grain_end_date = c.previous_end_date;
