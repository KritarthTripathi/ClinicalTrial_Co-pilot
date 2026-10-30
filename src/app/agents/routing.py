"""Routing for the supervisor and the sales router: a deterministic hint, an optional LLM decision, and a decision rule.
Pure functions (no LLM import) so the logic is unit-testable. Modes (env ROUTER_MODE):
  hybrid (default)  LLM always decides, rules supply a hint and can override
  fast              LLM only when the rules are unsure
  rules             rules only (no LLM)       llm   LLM only (no hint)"""
import json
import os
import re
from dataclasses import asdict, dataclass

from app.sales.semantic.catalog import (ACTIVITY_METRICS, AGENTS_CFG, ALIGN, LEVEL_COL, SUMMARY, ask_level, link_entities,
                                        resolve_metric, select_relations)

SUP_ROUTES = ["clinical", "sales", "out_of_scope"]
SALES_ROUTES = ["sales_geo", "sales_hcp", "sales_activity"]
MIN_CONF = AGENTS_CFG["thresholds"]["min_llm_confidence"]
FILE_RE = re.compile(r"[\w./\\:-]+\.(?:pdf|txt|md)\b", re.I)
CLINICAL_RE = re.compile(r"\b(protocols?|clinical trials?|trial protocols?|inclusion|exclusion|endpoints?|schedule of assessments|dosing regimen|eligibility)\b", re.I)
SALES_RE = re.compile(r"\b(trx|nbrx|nts|prescri\w*|scripts?|territor\w*|districts?|areas?|divisions?|hcps?|doctors?|prescribers?|reach|vae|calls?|suggested|engagements?|managed|managers?|office|address)\b", re.I)
METRIC_RE = re.compile(r"\b(trx|nbrx|nts|reach|vae|suggested|prescriptions?)\b", re.I)
UNSUPPORTED_RE = re.compile(r"\b(payers?|formulary|claims?|reject\w*|abandon\w*|call notes?|notes?|insights?|market share|goals?|attainment|quota|samples?|speaker|copay|revenue|price|competitors?|weather|jokes?|recipe|stocks?)\b", re.I)
ACT_RE = re.compile(r"\b(reach|vae|calls?|suggested|engagements?|have to make)\b", re.I)
HCP_RE = re.compile(r"\b(hcps?|doctors?|prescribers?|who|address|office|managed|managers?)\b", re.I)
AGENT_OF = {"v_activity_latest": "sales_activity", "v_geo_latest": "sales_geo", "v_geo_trend": "sales_geo", ALIGN: "sales_geo",
            SUMMARY: "sales_hcp", "v_hcp_rx_latest": "sales_hcp", "v_hcp_rx_trend": "sales_hcp"}


@dataclass
class Hint:
    route: str
    strong: bool
    reason: str


def supervisor_hint(q: str, known: dict) -> Hint:
    ql = q.lower()
    file = FILE_RE.search(q)
    clin = CLINICAL_RE.search(ql)
    ents = link_entities(q, known)
    sales = bool(SALES_RE.search(ql)) or bool(ents)
    metric = bool(METRIC_RE.search(ql))
    if file and (clin or not sales): return Hint("clinical", True, "file path with protocol wording")
    if clin and not sales: return Hint("clinical", bool(file), "protocol wording")
    if UNSUPPORTED_RE.search(ql) and not metric: return Hint("out_of_scope", True, "topic not in the datasets")
    if sales:
        n = len(set(m.lower() for m in SALES_RE.findall(ql)))
        return Hint("sales", bool(metric or n >= 2), "sales vocabulary")
    return Hint("out_of_scope", False, "no known topic")


def sales_hint(q: str, known: dict) -> Hint:
    ql = q.lower()
    ents = link_entities(q, known)
    cols = {c for c, _ in ents}
    metric = resolve_metric(q)
    rel = select_relations(q, ents, metric)[0]
    lvl = ask_level(q)
    act = len(ACT_RE.findall(ql)) + (2 if metric in ACTIVITY_METRICS else 0)
    hcp = len(HCP_RE.findall(ql)) + (1 if re.search(r"trend", ql) and not lvl else 0)
    geo = (2 if lvl else 0) + (1 if (not HCP_RE.search(ql) and cols & set(LEVEL_COL.values()) and re.search(r"\b(trx|nbrx|nts|prescriptions?)\b", ql)) else 0)
    scores = {"sales_activity": act, "sales_hcp": hcp, "sales_geo": geo}
    top = max(scores, key=scores.get)
    rest = sorted(scores.values())[:-1]
    strong = scores[top] >= 1 and max(rest) == 0
    return Hint(top if strong else AGENT_OF[rel], strong, f"scores {scores}")


def parse_llm_route(text: str, allowed: list):
    m = re.search(r"\{.*?\}", text or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except Exception:
        return None
    r = str(d.get("route", "")).strip()
    if r not in allowed:
        return None
    try:
        conf = float(d.get("confidence", 0.5))
    except Exception:
        conf = 0.5
    return {"route": r, "confidence": max(0.0, min(1.0, conf)), "reason": str(d.get("reason", ""))[:120]}


def decide(hint: Hint, llm, mode: str = "hybrid", min_conf: float = MIN_CONF) -> dict:
    base = {"hint": asdict(hint), "llm": llm, "mode": mode}
    if mode == "rules":
        return {**base, "final": hint.route, "method": "rules"}
    if mode == "llm":
        if llm is None or llm["confidence"] < min_conf:
            return {**base, "final": "clarify", "method": "llm_unusable", "options": [llm["route"]] if llm else []}
        return {**base, "final": llm["route"], "method": "llm"}
    if llm is None:                                                    # hybrid / fast without a usable LLM answer
        return {**base, "final": hint.route, "method": "rules_strong" if hint.strong else "rules_fallback"}
    if llm["route"] == hint.route:
        return {**base, "final": hint.route, "method": "agree"}
    if hint.strong:
        return {**base, "final": hint.route, "method": "rules_override"}   # the disagreement is visible in Phoenix
    if llm["confidence"] >= min_conf:
        return {**base, "final": llm["route"], "method": "llm_override"}
    return {**base, "final": "clarify", "method": "disagree_low_confidence", "options": [hint.route, llm["route"]]}


def route_level(level: str, question: str, known: dict, llm_fn=None, mode: str | None = None) -> dict:
    """level = 'supervisor' or 'sales'. llm_fn(question, hint) -> parsed dict or None (injected so tests need no model)."""
    mode = mode or os.getenv("ROUTER_MODE", "hybrid")
    hint = supervisor_hint(question, known) if level == "supervisor" else sales_hint(question, known)
    call = mode in ("hybrid", "llm") or (mode == "fast" and not hint.strong)
    llm = llm_fn(question, hint) if (call and llm_fn is not None) else None
    return decide(hint, llm, mode)
