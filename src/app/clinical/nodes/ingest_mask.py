"""Ingest + PII masking + compliance in ONE node so raw text never enters graph state
(and therefore never reaches checkpoints or Phoenix traces)."""
import uuid
from pathlib import Path

import pandas as pd

from app.common.config import settings
from app.common.pii import PIIMasker, compliance_report
from app.common.vault import PIIVault


def _read_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        import fitz  # pymupdf
        with fitz.open(path) as doc:
            return "\n".join(page.get_text() for page in doc)
    return path.read_text(encoding="utf-8", errors="ignore")


def ingest_mask_node(state: dict) -> dict:
    path = Path(state["input_path"])
    session_id = uuid.uuid4().hex[:12]
    masker = PIIMasker()
    update: dict = {"session_id": session_id, "attempts": 0, "errors": []}

    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
        for col in df.select_dtypes(include="object").columns:
            cache: dict = {}
            df[col] = df[col].map(lambda v: cache.setdefault(v, masker.mask(str(v))) if pd.notna(v) else v)
        out = Path(settings.work_dir) / f"{session_id}_masked.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False)
        sample = "\n".join(df.astype(str).head(200).apply(lambda r: " | ".join(r), axis=1))
        report = compliance_report(sample, masker.counts)
        update.update(doc_type="sales", masked_path=str(out))
    else:
        masked = masker.mask_document(_read_text(path))
        report = compliance_report(masked, masker.counts)
        update.update(doc_type="protocol", masked_doc=masked)

    PIIVault().save(session_id, masker.mapping)
    update["compliance"] = report
    return update
