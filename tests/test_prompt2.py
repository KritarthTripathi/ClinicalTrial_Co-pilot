from app.sales.semantic.catalog import build_prompt

END = "2025-12-29"


def test_channel_hint():
    assert "channel column" in build_prompt("Total TRx of our brand by payer channel", ["v_hcp_rx"], END)


def test_filter_column_rule():
    assert "only used in WHERE" in build_prompt("Total calls for Rheumatology doctors", ["v_hcp_activity"], END)


def test_month_example_and_no_current_date():
    p = build_prompt("NBRx per month for the last 3 months", ["v_hcp_rx"], END)
    assert "for the last 2 months" in p and "Never use CURRENT_DATE" in p
