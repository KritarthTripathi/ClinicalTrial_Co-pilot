"""LLM decisions for the supervisor and the sales router (JSON answers, parsed defensively)."""
from app.agents.routing import SALES_ROUTES, SUP_ROUTES, Hint, parse_llm_route
from app.common.llm import get_llm
from app.sales.semantic.catalog import AGENTS_CFG, SALES_AGENTS


def _ask(prompt: str) -> str:
    return get_llm("router").invoke(prompt).content


def supervisor_llm(question: str, hint: Hint | None):
    routes = "\n".join(f"- {k}: {v}" for k, v in AGENTS_CFG["supervisor"]["routes"].items())
    prompt = ("You are the supervisor of a pharma analytics system. Pick ONE route for the user's request.\nRoutes:\n" + routes +
              (f"\nRule-based suggestion (it may be wrong): {hint.route}" if hint else "") +
              '\nReturn only JSON: {"route": "clinical|sales|out_of_scope", "confidence": 0.0-1.0, "reason": "short"}'
              f"\nRequest: {question}\nJSON:")
    return parse_llm_route(_ask(prompt), SUP_ROUTES)


def sales_router_llm(question: str, hint: Hint | None):
    agents = "\n".join(f"- {k}: {v['description']}" for k, v in SALES_AGENTS.items() if k != "sales_all")
    prompt = ("You route a sales-analytics question to ONE specialist agent. Each agent can answer only from its own tables.\nAgents:\n" + agents +
              (f"\nRule-based suggestion (it may be wrong): {hint.route}" if hint else "") +
              '\nReturn only JSON: {"route": "sales_geo|sales_hcp|sales_activity", "confidence": 0.0-1.0, "reason": "short"}'
              f"\nQuestion: {question}\nJSON:")
    return parse_llm_route(_ask(prompt), SALES_ROUTES)
