from app.sales.semantic.catalog import RELATIONS, SALES_AGENTS, base_table, join_hints, scope


def test_each_agent_has_exactly_its_tables():
    assert set(SALES_AGENTS["sales_geo"]["tables"]) == {"territory_alignment_hierarchy", "rx_report_summary_geo"}
    assert set(SALES_AGENTS["sales_hcp"]["tables"]) == {"hcp_summary_with_territory_and_tm_info", "hcp_rx_summary_report", "territory_alignment_hierarchy"}
    assert set(SALES_AGENTS["sales_activity"]["tables"]) == {"territory_alignment_hierarchy", "hcp_summary_with_territory_and_tm_info", "hcp_activity_calls_vae_suggestions"}


def test_every_relation_reads_only_the_agents_own_tables():
    for a in ("sales_geo", "sales_hcp", "sales_activity"):
        for r in SALES_AGENTS[a]["relations"]:
            assert r in RELATIONS and base_table(r) in SALES_AGENTS[a]["tables"], (a, r)


def test_scopes_do_not_leak():
    assert "v_hcp_rx_latest" not in scope("sales_geo") and "v_activity_latest" not in scope("sales_geo")
    assert "v_geo_latest" not in scope("sales_hcp") and "v_activity_latest" not in scope("sales_hcp")
    assert "v_geo_latest" not in scope("sales_activity") and "v_hcp_rx_latest" not in scope("sales_activity")
    assert scope("sales_all") == set(RELATIONS)


def test_join_hints_per_agent():
    assert "never use JOIN" in " ".join(join_hints("sales_geo"))
    assert any("Semi-join only" in h for h in join_hints("sales_activity"))
    assert any("ON territory_name" in h for h in join_hints("sales_hcp"))
