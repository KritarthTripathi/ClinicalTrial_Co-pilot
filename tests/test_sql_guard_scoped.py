import pytest

from app.sales.sql_guard import guard

GEO = "SELECT SUM(trx) FROM v_geo_latest WHERE geo_level = 'AREA' AND grain_code = 'M'"
HCP = "SELECT hcp_ref_id, SUM(trx) FROM v_hcp_rx_latest WHERE grain_code = '13W' GROUP BY hcp_ref_id"


def test_each_agent_accepts_its_own_views_only():
    assert guard(GEO, "sales_geo") and guard(HCP, "sales_hcp")
    with pytest.raises(ValueError):
        guard(HCP, "sales_geo")
    with pytest.raises(ValueError):
        guard(GEO, "sales_hcp")
    with pytest.raises(ValueError):
        guard("SELECT SUM(activity_count) FROM v_activity_latest WHERE grain_code = 'W'", "sales_hcp")


def test_approved_join_passes_and_wrong_join_is_blocked():
    ok = ("SELECT r.hcp_ref_id FROM v_hcp_rx_latest r JOIN territory_alignment_hierarchy a ON a.territory_name = r.territory_name "
          "WHERE r.grain_code = '13W' AND a.territory_manager_name = '<TERRITORY_MANAGER_NAME_1>'")
    assert guard(ok, "sales_hcp")
    bad = ("SELECT s.hcp_ref_id FROM hcp_summary_with_territory_and_tm_info s JOIN v_hcp_rx_latest r ON s.hcp_ref_id = r.hcp_ref_id "
           "WHERE r.grain_code = '13W'")
    with pytest.raises(ValueError):
        guard(bad, "sales_hcp")


def test_semi_join_is_allowed():
    sql = ("SELECT SUM(activity_count) FROM v_activity_latest WHERE activity_type = 'CALL' AND grain_code = 'W' AND hcp_ref_id IN "
           "(SELECT hcp_ref_id FROM hcp_summary_with_territory_and_tm_info WHERE product_name = 'menji')")
    assert guard(sql, "sales_activity")
