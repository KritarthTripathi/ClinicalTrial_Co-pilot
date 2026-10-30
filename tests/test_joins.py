"""Consistency tests for the discovered joins (run from the project root; uses the CSV headers only)."""
from pathlib import Path

import yaml

J = yaml.safe_load(Path("src/app/sales/semantic/joins.yml").read_text())
COLS = {t: set(Path(f"data/schema_v2/{t}.csv").read_text().splitlines()[0].split(",")) for t in J["tables"]}


def pair(j):
    return {j["one"], j["many"]}


def test_every_join_column_exists_on_both_sides():
    for j in J["joins"]:
        for c in j["on"]:
            assert c in COLS[j["one"]] and c in COLS[j["many"]], j["id"]


def test_alignment_joins_on_territory_name():
    al = [j for j in J["joins"] if j["one"] == "territory_alignment_hierarchy"]
    assert len(al) >= 3 and all(j["on"] == ["territory_name"] for j in al)


def test_hcp_ref_id_alone_between_summary_and_rx_is_rejected():
    assert any({"hcp_summary_with_territory_and_tm_info", "hcp_rx_summary_report"} == set(r["tables"]) and r["on"] == ["hcp_ref_id"] for r in J["rejected"])
    ok = [j for j in J["joins"] if pair(j) == {"hcp_summary_with_territory_and_tm_info", "hcp_rx_summary_report"}]
    assert ok and ok[0]["on"] == ["hcp_ref_id", "product_name"]


def test_one_side_with_numbers_must_use_semi_join():
    for j in J["joins"]:
        if J["tables"][j["one"]]["metrics"] and j["cardinality"] != "one_to_one":
            assert j["safe_as"] == "semi_join", j["id"]


def test_geo_alignment_join_was_removed_by_owner():
    assert not [j for j in J["joins"] if "rx_report_summary_geo" in pair(j)]
    assert any(r["many"] == "rx_report_summary_geo" for r in J["removed_by_owner"])
