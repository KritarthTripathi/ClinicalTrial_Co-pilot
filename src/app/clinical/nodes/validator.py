import re

from app.common.config import settings


def _tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def _grounded(item: str, doc_tokens: set[str]) -> bool:
    t = _tokens(item)
    return bool(t) and len(t & doc_tokens) / len(t) >= 0.7


def validator_node(state: dict) -> dict:
    res = state.get("result", {})
    issues: list[str] = []

    if state["doc_type"] == "protocol":
        doc_tokens = _tokens(state["masked_doc"])
        for field in ("inclusion_criteria", "exclusion_criteria", "primary_endpoints",
                      "secondary_endpoints", "visits"):
            for item in res.get(field, []):
                if not _grounded(item, doc_tokens):
                    issues.append(f"{field}: not grounded in source: {item[:80]}")
        if not res.get("inclusion_criteria"):
            issues.append("no inclusion criteria extracted")
    else:
        if res.get("error"):
            issues.append(f"SQL error: {res['error']}")
        elif not res.get("rows"):
            issues.append("query returned no rows")

    ok = not issues
    retry = (not ok) and state.get("attempts", 0) <= settings.max_retries
    return {
        "validation": {"ok": ok, "issues": issues, "will_retry": retry},
        "feedback": "; ".join(issues[:5]),
    }
