import pytest

from app.sales.sql_guard import guard


def test_good_select_gets_limit():
    out = guard("SELECT hcp_id, SUM(trx) FROM v_hcp_rx GROUP BY hcp_id")
    assert "LIMIT 500" in out.upper()


def test_cte_allowed():
    assert guard("WITH t AS (SELECT hcp_id FROM v_hcp_rx) SELECT * FROM t")


@pytest.mark.parametrize("sql", [
    "DROP TABLE dim_hcp",
    "SELECT 1; SELECT 2",
    "SELECT * FROM dim_hcp",
    "SELECT * FROM read_csv('/etc/passwd')",
    "DELETE FROM fact_rx",
    "this is not sql",
])
def test_bad_sql_blocked(sql):
    with pytest.raises(ValueError):
        guard(sql)
