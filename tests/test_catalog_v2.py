from app.sales.semantic.catalog import ask_level, link_entities, make_plan, resolve_grain, resolve_metric, resolve_order

KNOWN = {"territory_name": ["cal_terr_6", "cal_terr_10"], "district_name": ["Cal1 district"], "area_name": ["California Area", "North East Area"],
         "division_name": ["Neuro", "GI"], "product_name": ["menji", "jalric"], "address_line": []}


def test_grain_defaults_and_words():
    assert resolve_grain("top prescribers of menji") == ("13W", False)
    assert resolve_grain("most recent week")[0] == "W"
    assert resolve_grain("in the last 4 weeks")[0] == "4W"
    assert resolve_grain("past month")[0] == "M"


def test_metric_resolution():
    assert resolve_metric("which area has the least NBRx") == "nbrx"
    assert resolve_metric("What was my VAE status") == "vae_status_pct"
    assert resolve_metric("How many suggested calls do I have to make") == "remaining_calls"
    assert resolve_metric("How many suggested VAE do I have to make") == "remaining_vae"
    assert resolve_metric("Who writes the most prescriptions") == "trx"


def test_order_and_limit():
    assert resolve_order("top 5 prescribers") == ("DESC", 5)
    assert resolve_order("who are the top prescribers") == ("DESC", 10)
    assert resolve_order("which area has the least TRx") == ("ASC", 1)
    assert resolve_order("which 3 territories are trending") == ("DESC", 3)


def test_levels_and_entities():
    assert ask_level("Which territory has the most TRx") == "TERRITORY"
    assert ask_level("Which hcps are managed by X") is None
    ents = dict(link_entities("TRx of cal_terr_6 and North East for menji", KNOWN))
    assert ents["territory_name"] == "cal_terr_6" and ents["area_name"] == "North East Area" and ents["product_name"] == "menji"
    assert "territory_name" in dict(link_entities("cal_terr_10 only", KNOWN)) and dict(link_entities("cal_terr_10 only", KNOWN))["territory_name"] == "cal_terr_10"


def test_geo_plan_always_has_level_and_grain():
    p = make_plan("Which area has the least NBRx in the latest month for the Neuro division?", KNOWN)
    t = p["template"]
    assert p["relations"][0] == "v_geo_latest" and "geo_level = 'AREA'" in t and "grain_code = 'M'" in t
    assert "division_name = 'Neuro'" in t and "ORDER BY nbrx ASC LIMIT 1" in t


def test_tm_uses_subquery_and_activity_formula():
    p = make_plan("What was my reach in the most recent week for the territory managed by <TERRITORY_MANAGER_NAME_5>", KNOWN)
    assert p["relations"][0] == "v_activity_latest" and "territory_alignment_hierarchy" in p["relations"]
    assert "NULLIF(SUM(suggested_engagements), 0)" in p["template"] and "<TERRITORY_MANAGER_NAME_5>" in p["template"]


def test_hcp_lists_and_trending():
    assert make_plan("Which hcps are prescribing menji in California Area?", KNOWN)["relations"][0] == "hcp_summary_with_territory_and_tm_info"
    t = make_plan("Top 5 trending HCPs in California Area for menji", KNOWN)
    assert t["relations"][0] == "v_hcp_rx_trend" and "previous_trx >= 10" in t["template"] and t["template"].endswith("LIMIT 5")
