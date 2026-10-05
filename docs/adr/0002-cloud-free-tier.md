# ADR 0002: Run in the cloud on free tiers, hybrid managed + self-hosted

- Status: accepted
- Date: 2026-10-05

## Context

The project should run the way a bank platform team runs systems: infrastructure as code,
managed databases, private networking, CI/CD with gated deploys, secrets outside the repo,
and cost guardrails. The budget is $0.

No single provider covers the stack for free. Managed Kafka and Temporal only offer
time-limited trials (Redpanda Serverless: $100 for 30 days; Confluent Cloud: 30-day credit),
which would delete our data after the trial.

## Decision

Hybrid: use **managed** services where a permanent free tier exists, and **self-host** the rest
on one Oracle Cloud Always Free ARM VM.

| Managed (permanent free tier) | Self-hosted on the VM |
| --- | --- |
| Neon Postgres: business data | Redpanda (Kafka API) |
| Neo4j AuraDB Free: entity graph | Temporal + its Postgres |
| Langfuse Cloud: LLM traces | MLflow (artifacts in OCI Object Storage) |
| Grafana Cloud: metrics, logs | |

Supporting choices:

- **Terraform** provisions everything on Oracle, with validation rules that refuse sizes beyond
  Always Free limits, plus a budget alert at the first cent.
- **No public service ports.** Only break-glass SSH from one IP. Everything else goes over
  Tailscale, mirroring a bank's private network and zero-trust access.
- **GitHub Actions** deploys after CI passes, through a protected `production` environment,
  joining the tailnet as an ephemeral, tagged node.
- **Codespaces** as the standard dev environment (devcontainer), so setup is reproducible.
- **Schema migrations** run on every deploy, using the direct (non-pooled) Neon connection.

## Alternatives considered

| Option | Why not |
| --- | --- |
| Everything on one VM | Misses managed-service experience (pooling, branching, serverless scale-to-zero) |
| Managed Kafka trial | Data deleted after 30 days |
| AWS/GCP/Azure credits | Expire in 1-12 months; easy to run up a bill by mistake |
| Kubernetes from day one | 12 GB RAM is tight; k3s arrives in Step 9 on the same VM |

## Consequences

- Two networks to reason about: public managed services (TLS + passwords) and the private
  tailnet. In a bank, managed services would sit behind private endpoints instead.
- Free-tier limits shape the design: Neon 1 GB fits `SIZE=small` and `medium` data, not `full`.
- Oracle can change free limits without notice (it halved ARM capacity in mid-2026). The
  Terraform validations and budget alert are the protection.
- Gemini's free tier may use prompts for training, so only synthetic data is ever sent, and the
  LLM gateway (Step 4) masks PII regardless.
