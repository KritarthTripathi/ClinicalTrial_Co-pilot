from app.agents.routing import Hint, decide, parse_llm_route, route_level, sales_hint, supervisor_hint

KNOWN = {"territory_name": ["cal_terr_6"], "district_name": ["Cal1 district"], "area_name": ["California Area"],
         "division_name": ["Neuro", "GI"], "product_name": ["menji", "jalric"], "address_line": []}


def test_supervisor_rules():
    assert supervisor_hint("Parse the protocol at data/synthetic/protocol_001.txt", KNOWN).route == "clinical"
    assert supervisor_hint("Which territory has the most TRx for menji?", KNOWN).route == "sales"
    h = supervisor_hint("Which payer has the highest reject rate?", KNOWN)
    assert h.route == "out_of_scope" and h.strong
    assert supervisor_hint("Tell me a joke", KNOWN).route == "out_of_scope"


def test_sales_router_rules():
    assert sales_hint("Which territory has the most TRx for menji?", KNOWN).route == "sales_geo"
    assert sales_hint("Who are the top 5 prescribers of menji?", KNOWN).route == "sales_hcp"
    assert sales_hint("What was my reach in the most recent week for California Area?", KNOWN).route == "sales_activity"
    assert sales_hint("How many suggested VAE do I have to make for cal_terr_6?", KNOWN).route == "sales_activity"


def test_parse_llm_route():
    r = parse_llm_route('Sure! {"route": "sales", "confidence": 0.9, "reason": "x"}', ["sales", "clinical"])
    assert r == {"route": "sales", "confidence": 0.9, "reason": "x"}
    assert parse_llm_route("no json", ["sales"]) is None
    assert parse_llm_route('{"route": "nope"}', ["sales"]) is None


def test_decide_cases():
    strong, weak = Hint("sales", True, ""), Hint("sales", False, "")
    assert decide(strong, {"route": "sales", "confidence": 0.5, "reason": ""})["method"] == "agree"
    d = decide(strong, {"route": "out_of_scope", "confidence": 0.95, "reason": ""})
    assert d["final"] == "sales" and d["method"] == "rules_override"
    d = decide(weak, {"route": "out_of_scope", "confidence": 0.9, "reason": ""})
    assert d["final"] == "out_of_scope" and d["method"] == "llm_override"
    d = decide(weak, {"route": "out_of_scope", "confidence": 0.3, "reason": ""})
    assert d["final"] == "clarify" and set(d["options"]) == {"sales", "out_of_scope"}
    assert decide(weak, None)["method"] == "rules_fallback" and decide(strong, None)["method"] == "rules_strong"
    assert decide(strong, None, "llm")["final"] == "clarify"
    assert decide(weak, None, "rules")["final"] == "sales"


def test_route_level_modes_call_the_llm_only_when_needed():
    calls = []
    fake = lambda q, h: calls.append(1) or {"route": h.route, "confidence": 0.9, "reason": ""}
    route_level("supervisor", "Which territory has the most TRx?", KNOWN, fake, "rules")
    route_level("supervisor", "Which territory has the most TRx?", KNOWN, fake, "fast")      # strong hint: no LLM call
    assert calls == []
    route_level("supervisor", "Which territory has the most TRx?", KNOWN, fake, "hybrid")
    assert calls == [1]
