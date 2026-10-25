"""Deterministic PII detection and masking (Presidio + spaCy + custom recognizers).
Fully local. Add an LLM/GLiNER pass for contextual identifiers as a second layer."""
import re
from collections import Counter
from functools import lru_cache

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider

ENTITIES = [
    "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "US_SSN", "LOCATION",
    "IP_ADDRESS", "URL", "MRN", "SUBJECT_ID", "DATE_OF_BIRTH",
]
# Deterministic identifiers: any residual after masking blocks the document.
HIGH_RISK = {"EMAIL_ADDRESS", "PHONE_NUMBER", "US_SSN", "MRN", "SUBJECT_ID", "DATE_OF_BIRTH", "IP_ADDRESS"}
PLACEHOLDER_RE = re.compile(r"<[A-Z_]+_\d+>")
# business terms that are NOT personal data (fictional brands, payer channels)
ALLOW_LIST = ["Aurelis", "Clearon", "Psorix", "Medicaid", "Medicare"]


@lru_cache(maxsize=1)
def get_analyzer() -> AnalyzerEngine:
    nlp = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}],
    }).create_engine()
    registry = RecognizerRegistry()
    registry.load_predefined_recognizers(nlp_engine=nlp)

    def pat(entity, name, regex, score=0.85):
        registry.add_recognizer(PatternRecognizer(
            supported_entity=entity, patterns=[Pattern(name, regex, score)]))

    pat("MRN", "mrn", r"\bMRN[-:\s#]*\d{6,10}\b")
    pat("SUBJECT_ID", "subj", r"\bSUBJ-\d{3,6}\b")
    pat("DATE_OF_BIRTH", "dob", r"\b(?:DOB|Date of Birth)[:\s]*\d{1,2}/\d{1,2}/\d{4}\b")
    pat("PHONE_NUMBER", "us_phone", r"\(?\b\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b")
    pat("EMAIL_ADDRESS", "email_regex", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", 0.95)
    return AnalyzerEngine(registry=registry, nlp_engine=nlp, supported_languages=["en"])

PRIORITY = {"MRN": 0, "SUBJECT_ID": 0, "DATE_OF_BIRTH": 0, "EMAIL_ADDRESS": 1, "PHONE_NUMBER": 1}
class PIIMasker:
    """Stateful per document: same original -> same placeholder, map kept for the vault."""

    def __init__(self):
        self.analyzer = get_analyzer()
        self.mapping: dict[str, str] = {}
        self._reverse: dict[tuple, str] = {}
        self._n: Counter = Counter()
        self.counts: Counter = Counter()

    def _placeholder(self, entity: str, original: str) -> str:
        key = (entity, original)
        if key not in self._reverse:
            self._n[entity] += 1
            ph = f"<{entity}_{self._n[entity]}>"
            self._reverse[key] = ph
            self.mapping[ph] = original
        return self._reverse[key]

    def mask(self, text: str) -> str:
        if not text.strip():
            return text
        results = self.analyzer.analyze(text=text, language="en", entities=ENTITIES, score_threshold=0.4, allow_list=ALLOW_LIST)
        results = sorted(results, key=lambda r: (r.start, -(r.end - r.start),
                         PRIORITY.get(r.entity_type, 2), -r.score))
        out, pos = [], 0
        for r in results:
            if r.start < pos:   # skip overlaps
                continue
            out.append(text[pos:r.start])
            out.append(self._placeholder(r.entity_type, text[r.start:r.end]))
            self.counts[r.entity_type] += 1
            pos = r.end
        out.append(text[pos:])
        return "".join(out)

    def mask_document(self, text: str) -> str:
        return "\n".join(self.mask(line) for line in text.split("\n"))


def residual_scan(text: str) -> Counter:
    """Re-scan already-masked text; anything found is PII that slipped through."""
    clean = PLACEHOLDER_RE.sub(" ", text)
    found: Counter = Counter()
    for line in clean.split("\n"):
        if not line.strip():
            continue
        for r in get_analyzer().analyze(text=line, language="en", entities=ENTITIES, score_threshold=0.5, allow_list=ALLOW_LIST):
            found[r.entity_type] += 1
    return found


def compliance_report(masked_text: str, masked_counts: Counter) -> dict:
    """Config-driven policy would go here (HIPAA Safe Harbor 18, GDPR special categories).
    Reports counts and entity types only, never values."""
    residual = residual_scan(masked_text)
    blocking = {k: v for k, v in residual.items() if k in HIGH_RISK}
    return {
        "masked_entities": dict(masked_counts),
        "residual_entities": dict(residual),
        "verdict": "blocked" if blocking else "pass",
        "reason": f"residual high-risk identifiers: {sorted(blocking)}" if blocking else "",
        "policy": "hipaa_safe_harbor_subset_v0",
    }
