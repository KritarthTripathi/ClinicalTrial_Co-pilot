# Shared design notes (applies to every dataset)

Principle: keep it simple and consistent. Synthetic data only needs to be believable, not identical to a real company.

## Master reference (dataset 1 is the source of truth)
- File: hcp-summary-with-territory-and-tm-info.csv (500 rows, 269 unique HCPs). Later datasets reuse these keys; no new HCPs are invented.
- Join keys: hcp_ref_id (format HCP_000001..HCP_999999), product_name, territory_name, district_name, area_name, division_name.
- Territory map: territory-reference-map.csv (48 territories, one TM each, one division each).

## Conventions
- Column names: lowercase snake_case (hyphens become underscores). Table names likewise.
- Division codes: CMH, GI, IMM, OBU, Neuro.
- Products (lowercase, as given): CMH menji/zent/flend; GI enu/unienz; IMM glisol/perlio; OBU jalric/vizneri/venclyx; Neuro kolisna/brainic/neuric.
- Geography: 4 areas (California Area, Mid Atlantic Area, New York Area, North East Area) x 4 districts (Cal1..4, Mid1..4, Ny1..4, Ne1..4 "district") x 3 territories (cal_terr_1..12, mid_terr_1..12, ny_terr_1..12, ne_terr_1..12).
- Each territory belongs to exactly one division and has exactly one TM; districts mix divisions.
- States: 2-letter codes (CA, PA, NJ, MD, VA, NY, MA, CT, RI, ME).
- An HCP has one division, one territory, one address; products come from that division only.

## Rules for new datasets
- Row counts as requested; no completely identical rows.
- Numbers must reconcile across datasets (for example HCP-level Rx rolls up to payer-level Rx).
- Sensitive columns (flag for the privacy policy): person names, emails, free-text notes/insights.
- Typed TM names/emails in questions get masked with the same mapping as the database.

## Dataset 2: hcp-rx-summary-report (v3, explicit period dates)
- 6000 rows = 500 HCP-product pairs x 4 grains (W, 4W, M, 13W) x 3 consecutive periods (latest, previous, the one before). Rows go beyond 5000 so every grain is complete for every pair.
- Reporting is WEEKLY: weeks run Friday..Thursday, every period ends on a Thursday; the count restarts after each report.
- Periods: W = 1 week; 4W = 4 weeks; 13W = 13 weeks; M = the weeks whose Thursday falls in one calendar month (4 or 5 weeks). Latest period of every grain ends 2026-01-29.
- Columns: hcp_ref_id, hcp_full_name, territory_name, district_name, area_name, division_name, product_name, trx, nbrx, nts, grain_code, grain_start_date, grain_end_date, previous_start_date, previous_end_date (ISO YYYY-MM-DD).
- previous_start_date/previous_end_date = the immediately preceding period of the same grain. A row for it exists in the table except for the oldest period (k=2), which has no earlier row.
- Latest period for a grain = the row with MAX(grain_end_date) for that grain.
- Agent rules: no date and no grain given -> grain_code 13W, latest period, order by trx descending.
- 'Trending' = compare a row with its previous-period row (join on hcp, product, grain_code, previous dates = grain dates), e.g. (trx - previous trx) / previous trx, with a minimum previous volume.
- Built from a daily simulation (_sim/_sim-daily-hcp-product-rx.csv, 273 days). Payer/plan datasets must be derived from this daily table so totals reconcile.
- NTS definition still to be confirmed; assumed nts <= trx, independent of nbrx.

## Dataset 3: hcp-activity-calls-vae-suggestions
- 6456 rows = 269 unique HCPs (every HCP in dataset 1) x activity_type (CALL, VAE) x 4 grains x 3 consecutive periods. No product_name: activity is at HCP level.
- Same grain/period dates as dataset 2 (weeks end Thursday; latest period ends 2026-01-29; previous_* dates point to the preceding period).
- Columns: hcp_ref_id, hcp_full_name, territory_name, district_name, area_name, division_name, activity_type, suggested_engagements (0-9), activity_count (0-9), grain_code, grain_start_date, grain_end_date, previous_start_date, previous_end_date.
- activity_count never exceeds suggested_engagements (same week). Suggestions are capped so each 13-week period stays within 0-9.
- Every territory has at least one suggested CALL and VAE in each of the last 3 weeks, so latest-week reach is never 0/0. Other grains/periods are not guaranteed; the agent should use NULLIF in divisions.
- Formulas: reach % = SUM(activity_count) / SUM(suggested_engagements) x 100 for activity_type = CALL (VAE status the same with VAE); remaining = suggested_engagements - activity_count per HCP, descending, limit 10.
- Built from a weekly simulation (_sim/_sim-weekly-hcp-activity.csv); planted low call-reach / high / low VAE territories in _sim/_sim-activity-truth.json. Bigger prescribers get more suggestions.

## Dataset 4: territory-alignment-hierarchy
- Same content as territory-reference-map.csv (48 rows, one per territory): area_name, district_name, territory_name, division_name, state, territory_manager_name, territory_manager_email.
- Fully consistent with dataset 1 (checked). Add extra columns only if the user asks.

## Dataset 5: rx_report_summary_geo (roll-up of dataset 2)
- 3852 rows = complete grid of geo unit x product of its division x 4 grains x 3 periods: TERRITORY 1536, DISTRICT 1536, AREA 624, DIVISION 156. Zero rows kept where nobody in a unit writes a product.
- Columns: geo_level (TERRITORY/DISTRICT/AREA/DIVISION), area_name, district_name, territory_name, division_name, product_name, trx, nbrx, nts, grain_code, grain_start_date, grain_end_date, previous_start_date, previous_end_date.
- Lower-level name columns hold 'ALL' above their level (AREA rows: district_name = territory_name = 'ALL'; DIVISION rows: area, district, territory = 'ALL').
- Every value is a SUM of HCP rows in hcp-rx-summary-report, so all levels reconcile with the HCP data.
- AGENT RULE: always filter geo_level (rows of different levels overlap; summing across levels double counts). Summing across product_name within one level is correct (for example a whole division).
- Same defaults as dataset 2: no date and no grain -> 13W, latest period (MAX(grain_end_date)), order by trx descending. 'Latest month' = grain_code M, latest period.
