# AML Investigation Copilot

An AI system that helps anti-money-laundering investigators triage alerts, gather evidence and
draft suspicious transaction reports, with a human making every final decision.

> Core principle: **a deterministic workflow wraps a non-deterministic agent.**
> The agent gathers and drafts; the workflow controls state; a human decides.

Status: **Step 1 of 10 - Foundation.** See `docs/adr/0001-architecture.md` for the design.

## Architecture

| Layer | Purpose | Tech |
| --- | --- | --- |
| Data | Stream, validate, store, features, entity graph | Redpanda, Postgres, Parquet, Feast, Neo4j |
| Detection | Rules baseline + ML risk scorer with explanations | LightGBM, SHAP, MLflow |
| Orchestration | Durable case workflow, retries, SLAs, human signals | Temporal |
| Agent | Read-only tools, bounded graph, structured case file | LangGraph, pgvector |
| LLM gateway | PII masking, routing, budgets, logging | LiteLLM |
| Human review | Queue, evidence, cited draft, approve/edit/reject | FastAPI, Streamlit |
| Governance | Eval gates, tracing, drift, append-only audit, replay | pytest, Langfuse, Evidently |

## Quick start

Prerequisites: Docker Desktop (or Docker Engine), [uv](https://docs.astral.sh/uv/), `make`, git.
Windows users: run everything inside WSL2.

```bash
cp .env.example .env          # then edit passwords
make install                  # Python deps + pre-commit hooks
make up-lite                  # Postgres + Redpanda   (or `make up` for the full stack)
make data-synthetic           # small generated dataset, no download needed
make load                     # into Postgres; safe to run twice
make check                    # lint + types + unit tests
make test-int                 # integration tests against the running DB
```

### Running in the cloud (free tier)

The production-style setup uses Oracle Cloud Always Free (VM via Terraform), Neon Postgres,
Neo4j AuraDB Free, Tailscale and GitHub Actions, all at $0/month.
Full walkthrough: [`docs/cloud-setup.md`](docs/cloud-setup.md). Design rationale:
[`docs/adr/0002-cloud-free-tier.md`](docs/adr/0002-cloud-free-tier.md).

```bash
make cloud-init cloud-plan cloud-apply   # Oracle VM, network, bucket, budget alert
make migrate                             # schema -> Neon
make cloud-deploy                        # Redpanda, Temporal, MLflow -> VM + smoke tests
make cloud-load cloud-test-int           # data -> Neon, integration tests
```

### Using the real IBM dataset

1. Create a Kaggle API token (kaggle.com -> Settings -> API) and save it to `~/.kaggle/kaggle.json`.
2. `make download` (about 475 MB)
3. `make data SIZE=small` (100k rows), `SIZE=medium` (1M) or `SIZE=full` (~5M)
4. `make load`

## Service URLs (full stack)

| Service | URL |
| --- | --- |
| Postgres | `localhost:5432` |
| Redpanda (Kafka API) | `localhost:19092` |
| Neo4j browser | http://localhost:7474 |
| Temporal UI | http://localhost:8080 |
| MLflow | http://localhost:5000 |

## Repo layout

```
src/aml/
  config.py      typed settings (AML_* env vars)
  data/          contracts, IBM loader, synthetic generator, KYC profiles, Postgres loader
  features/      Step 2
  detection/     Step 3
  agent/         Step 4
  gateway/       Step 4
  workflow/      Step 5
  ui/            Step 8
  evals/         Step 7
infra/postgres/  schema (raw, ref, cases + append-only audit log)
docs/adr/        architecture decision records
tests/           unit + integration tests
```

## Data notice

All data is synthetic: IBM's AML transaction simulation plus generated customer profiles.
Results demonstrate the method, not real-world performance.
