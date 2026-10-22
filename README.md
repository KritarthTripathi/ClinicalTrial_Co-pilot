# Zero-Bytes-Out Multi-Agent Framework

Local-first multi-agent pipeline that parses **clinical trial protocols** and **sales analytics**
with **no external LLM API calls**. Ollama (open-weight models) + LangGraph (stateful agents) +
Presidio (PII masking and compliance) + Arize Phoenix (self-hosted tracing).
Built on a synthetic-data Azure VM, designed to move to an air-gapped on-prem box unchanged.

```
input → ingest_mask (parse + PII mask + compliance) ──blocked──► END
              │ pass
              ├─ protocol agent (section-aware chunking, Pydantic structured output)
              └─ sales agent (LLM writes SQL → read-only DuckDB)
                        ↓
                    validator (grounding / SQL checks) ──retry (bounded)──► specialist
                        ↓
                      output (optional local re-identification)
```

## Design decisions 
- **Raw text never enters graph state.** Masking happens inside the ingest node, so checkpoints and Phoenix traces only ever hold masked content. The placeholder→original map lives in an encrypted vault (Fernet key via docker secret), outside state.
- **Deterministic PII first** (Presidio + spaCy + custom MRN/subject-ID/DOB/phone recognizers), with a residual re-scan as the compliance gate. To Do: Add an LLM/GLiNER contextual pass as a second layer.
- **Enforced network isolation:** `internal: true` Docker network, plus `scripts/egress_test.sh` that fails if anything can reach the internet.
- **LLM is a config value** (`src/app/llm.py`); no cloud SDKs in app code; secrets behind an interface.
- **Model-generated SQL is constrained:** single SELECT only, keyword denylist, DuckDB external access disabled. (Production hardening: run in a network-less sandbox container.)
- **Measured masking recall** against planted ground truth (`scripts/measure_recall.py`).

## Quick start (connected machine / Azure staging phase)
```bash
sh scripts/gen_key.sh                                   # PII vault key (docker secret)
docker compose build
docker compose --profile setup run --rm ollama-setup   # one-time model pull (only job with internet)
docker compose up -d                                    # add -f docker-compose.gpu.yml on a GPU host
python3 scripts/generate_synthetic.py                   # synthetic protocol + sales data

docker compose run --rm app python -m app.main data/synthetic/protocol_001.txt
docker compose run --rm app python -m app.main data/synthetic/sales_001.csv --question "Revenue by region"
docker compose run --rm app python scripts/measure_recall.py
docker compose run --rm app pytest -q tests
sh scripts/egress_test.sh                               # must print OK
```
Phoenix UI: http://localhost:6006 (on Azure, via SSH tunnel through Bastion).

## Azure → on-prem
1. `infra/azure/provision.sh` (illustrative; review first). Use synthetic data only.
2. `scripts/bundle_offline.sh`, then rebuild from the bundle with the network off.
3. On-prem: install Docker + NVIDIA Container Toolkit, load the bundle, run `egress_test.sh`, capture `tcpdump` during a full run, keep the evidence.

## Known gaps / next steps / TO DO items
- Add a GLiNER or LLM contextual-PII layer and a config-driven HIPAA/GDPR policy file.
- Replace the compliance `blocked` edge with a LangGraph `interrupt()` for review.
- Phoenix Evals with a local judge model (hallucination, extraction accuracy).
- Pin dependencies (`pip freeze > requirements.lock`) once the stack builds.
- Verify the Phoenix telemetry-disable variable and Azure extension names against current docs.
