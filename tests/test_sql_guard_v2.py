import pytest

from app.sales.sql_guard import guard


def test_good_queries_pass_and_get_limit():
    assert "LIMIT" in guard("SELECT hcp_ref_id, SUM(trx) FROM v_hcp_rx_latest WHERE grain_code = '13W' GROUP BY hcp_ref_id").upper()
    assert guard("SELECT SUM(trx) FROM v_geo_latest WHERE geo_level = 'AREA' AND grain_code = 'M'")
    assert guard("SELECT DISTINCT hcp_ref_id FROM hcp_summary_with_territory_and_tm_info WHERE territory_manager_name = '<TERRITORY_MANAGER_NAME_1>'")


def test_subquery_on_alignment_table_is_allowed():
    sql = ("SELECT SUM(trx) FROM v_geo_latest WHERE geo_level = 'TERRITORY' AND grain_code = 'M' AND territory_name = "
           "(SELECT territory_name FROM territory_alignment_hierarchy WHERE territory_manager_name = '<TERRITORY_MANAGER_NAME_1>')")
    assert guard(sql)


@pytest.mark.parametrize("sql", [
    "SELECT SUM(trx) FROM v_hcp_rx_latest",                                           # missing grain_code
    "SELECT SUM(trx) FROM v_geo_latest WHERE grain_code = '13W'",                      # missing geo_level
    "SELECT * FROM hcp_rx_summary_report",                                            # base period table not allowed
    "SELECT * FROM rx_report_summary_geo WHERE geo_level = 'AREA'",
    "SELECT SUM(trx) FROM v_hcp_rx_latest WHERE grain_code = '13W' AND week > CURRENT_DATE",
    "DROP TABLE territory_alignment_hierarchy",
    "SELECT 1; SELECT 2",
    "SELECT * FROM read_csv('/etc/passwd')",
])
def test_bad_sql_blocked(sql):
    with pytest.raises(ValueError):
        guard(sql)
