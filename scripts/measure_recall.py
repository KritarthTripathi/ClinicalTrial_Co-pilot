"""Masking recall = fraction of planted PII strings that no longer appear in masked output.
Recall matters more than precision for PII. Run inside the app container."""
import json
from pathlib import Path

import pandas as pd

from app.common.pii import PIIMasker

planted = json.loads(Path("data/synthetic/planted_pii.json").read_text())
m = PIIMasker()
masked_protocol = m.mask_document(Path("data/synthetic/protocol_001.txt").read_text())
df = pd.read_csv("data/synthetic/sales_001.csv")
masked_sales = "\n".join(df.astype(str).apply(lambda r: " | ".join(m.mask(v) for v in r), axis=1))
blob = masked_protocol + "\n" + masked_sales

leaked = [p for p in planted if p in blob]
print(f"planted={len(planted)} leaked={len(leaked)} recall={1 - len(leaked) / len(planted):.3f}")
for p in leaked:
    print("  LEAKED:", p)
