from app.sales.semantic.catalog import make_plan

K = {"territory_name": ["cal_terr_6"], "district_name": ["Cal1 district"], "area_name": ["California Area"], "division_name": ["Neuro"],
     "product_name": ["menji"], "address_line": ["12 Oak Street, Suite 100"]}


def test_geo_agent_uses_only_geo_relations():
    p = make_plan("Which area has the least NBRx in the latest month for the Neuro division?", K, "sales_geo")
    assert p["relations"] == ["v_geo_latest"] and "geo_level = 'AREA'" in p["template"] and "JOIN" not in p["template"]


def test_agents_refuse_questions_outside_their_tables():
    assert make_plan("Which area has the least NBRx in the latest month for the Neuro division?", K, "sales_hcp")["out_of_scope"]
    assert make_plan("Top 5 prescribers of menji", K, "sales_activity")["out_of_scope"]
    assert make_plan("What was my reach in the most recent week for California Area?", K, "sales_geo")["out_of_scope"]
    assert make_plan("Which hcps write at 12 Oak Street, Suite 100?", K, "sales_geo")["out_of_scope"]


def test_activity_agent_filters_by_product_with_a_semi_join():
    p = make_plan("What was my reach in the most recent week for HCPs prescribing menji in California Area?", K, "sales_activity")
    assert "hcp_ref_id IN (SELECT hcp_ref_id FROM hcp_summary_with_territory_and_tm_info WHERE product_name = 'menji')" in p["template"]
    assert "JOIN" not in p["template"] and "hcp_summary_with_territory_and_tm_info" in p["relations"]


def test_hcp_agent_address_ranking_and_listing():
    p = make_plan("Who are the top 5 prescribers in the last 13 weeks at the office address 12 Oak Street, Suite 100?", K, "sales_hcp")
    assert p["relations"][0] == "v_hcp_rx_latest" and "address_line = '12 Oak Street, Suite 100'" in p["template"]
    assert make_plan("Which hcps write at 12 Oak Street, Suite 100?", K, "sales_hcp")["relations"] == ["hcp_summary_with_territory_and_tm_info"]


def test_territory_manager_lookup_is_a_subquery_not_a_join():
    p = make_plan("What is the TRx of <TERRITORY_MANAGER_NAME_3> in the latest month?", K, "sales_geo")
    assert "territory_name = (SELECT territory_name FROM territory_alignment_hierarchy WHERE territory_manager_name = '<TERRITORY_MANAGER_NAME_3>')" in p["template"]
    assert "JOIN" not in p["template"]
