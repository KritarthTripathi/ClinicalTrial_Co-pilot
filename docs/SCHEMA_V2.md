# Schema v2 (generated from metrics.yml)

Defaults: grain_code = 13W; no metric -> trx; ranking -> highest first. `*_latest` views hold only the latest period of each grain; `*_trend` views add the previous period.

## Relations the agent may query

### hcp_summary_with_territory_and_tm_info  (table)
One row per HCP and per product the HCP prescribes, with office address, territory, district, area, division and territory manager.

Columns: hcp_ref_id, hcp_full_name, address_line, city, state, territory_name, district_name, area_name, division_name, territory_manager_name, territory_manager_email, product_name

- Use for: which HCPs write at an office address, which HCPs prescribe a product in a territory/district/area, which HCPs a territory manager manages.
- Return DISTINCT hcp_ref_id and hcp_full_name.

### territory_alignment_hierarchy  (table)
One row per territory: area, district, division, state and the territory manager (name and email).

Columns: area_name, district_name, territory_name, division_name, state, territory_manager_name, territory_manager_email

- Use to translate a territory manager into a territory, or to list districts and territories of an area.

### v_hcp_rx_latest  (view)
Latest period of HCP prescriptions. One row per HCP, product and grain_code.

Columns: hcp_ref_id, hcp_full_name, territory_name, district_name, area_name, division_name, product_name, trx, nbrx, nts, grain_code, grain_start_date, grain_end_date

- Always filter grain_code. To rank HCPs SUM the metric and GROUP BY hcp_ref_id, hcp_full_name.

### v_hcp_rx_trend  (view)
Latest period next to the previous period, per HCP and product. trx_change_pct is the percent change of trx versus previous_trx.

Columns: hcp_ref_id, hcp_full_name, territory_name, district_name, area_name, division_name, product_name, grain_code, trx, nbrx, nts, previous_trx, previous_nbrx, previous_nts, trx_change, trx_change_pct

- Trending up = highest trx_change_pct; require previous_trx >= 10 so tiny numbers do not dominate.

### v_activity_latest  (view)
Latest period of calls and approved emails (VAE) per HCP. suggested_engagements = suggested, activity_count = done.

Columns: hcp_ref_id, hcp_full_name, territory_name, district_name, area_name, division_name, activity_type, suggested_engagements, activity_count, grain_code, grain_start_date, grain_end_date

- activity_type is 'CALL' or 'VAE'. Always filter grain_code and activity_type.
- Use NULLIF when dividing.

### v_geo_latest  (view)
Latest period of prescriptions rolled up by geography. geo_level is TERRITORY, DISTRICT, AREA or DIVISION.

Columns: geo_level, area_name, district_name, territory_name, division_name, product_name, trx, nbrx, nts, grain_code, grain_start_date, grain_end_date

- Always filter geo_level AND grain_code (levels overlap: never add up different levels).
- Name columns below the row's level contain 'ALL'. SUM across product_name is correct.

### v_geo_trend  (view)
Geo roll-up of the latest period next to the previous period.

Columns: geo_level, area_name, district_name, territory_name, division_name, product_name, grain_code, trx, nbrx, nts, previous_trx, previous_nbrx, previous_nts

- Always filter geo_level AND grain_code. Percent change = (SUM(trx) - SUM(previous_trx)) * 100.0 / NULLIF(SUM(previous_trx), 0).

## Metrics

- **trx**: Total prescriptions (TRx) = `SUM(trx)`
- **nbrx**: New-to-brand prescriptions (NBRx) = `SUM(nbrx)`
- **nts**: NTS (definition to be confirmed) = `SUM(nts)`
- **reach_pct**: Call reach % = `SUM(activity_count) * 100.0 / NULLIF(SUM(suggested_engagements), 0)` where activity_type = 'CALL'
- **vae_status_pct**: VAE status % = `SUM(activity_count) * 100.0 / NULLIF(SUM(suggested_engagements), 0)` where activity_type = 'VAE'
- **remaining_calls**: Suggested calls still to make, per HCP = `suggested_engagements - activity_count` where activity_type = 'CALL'
- **remaining_vae**: Suggested VAE still to send, per HCP = `suggested_engagements - activity_count` where activity_type = 'VAE'

## Global rules

- Return exactly ONE SELECT statement and nothing else.
- Use only the listed relations and only their listed columns.
- Never use CURRENT_DATE or NOW(): the data is fixed.
- To filter by a territory manager use: territory_name = (SELECT territory_name FROM territory_alignment_hierarchy WHERE territory_manager_name = '<value>').