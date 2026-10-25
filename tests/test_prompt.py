from app.sales.semantic.catalog import build_prompt

END = "2025-12-29"


def test_no_date_rule_without_time_words():
    assert "week_start >" not in build_prompt("VAE open rate by specialty", ["v_hcp_activity"], END)


def test_date_rule_for_last_weeks():
    assert f"DATE '{END}'" in build_prompt("Top 10 doctors in the last 13 weeks", ["v_hcp_rx"], END)


def test_is_ours_rule_only_for_our_brand():
    assert "is_ours" not in build_prompt("VAE open rate by specialty", ["v_hcp_activity"], END).split("Examples:")[0].split("Rules:")[1]
    assert "Aurelis" in build_prompt("TRx of our brand by state", ["v_hcp_rx"], END)


def test_ranking_and_having_rules():
    assert "ORDER BY the aggregate DESC" in build_prompt("Which 5 doctors received the most calls?", ["v_hcp_activity"], END)
    assert "HAVING" in build_prompt("How many doctors received more than 20 calls?", ["v_hcp_activity"], END)


def test_prescriptions_maps_to_trx():
    assert "SUM(trx)" in build_prompt("Top 10 doctors by prescriptions of our brand", ["v_hcp_rx"], END)


def test_monthly_view_never_uses_is_ours():
    p = build_prompt("Total calls and TRx of our brand for Dermatology doctors", ["v_hcp_monthly"], END)
    assert "do NOT use is_ours" in p and "single row" in p


def test_last_months_has_no_date_filter():
    p = build_prompt("NBRx per month for the last 3 months", ["v_hcp_rx"], END)
    assert "do NOT filter by date" in p
