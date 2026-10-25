import pytest

from app.sales.sql_guard import guard


@pytest.mark.parametrize("sql", [
    "SELECT SUM(trx) FROM v_hcp_rx WHERE week_start > CURRENT_DATE - INTERVAL 30 DAY",
    "SELECT SUM(trx) FROM v_hcp_rx WHERE week_start > NOW() - INTERVAL 30 DAY",
])
def test_current_time_blocked(sql):
    with pytest.raises(ValueError):
        guard(sql)
