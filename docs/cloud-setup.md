# Cloud setup (free tier)

Total cost: **$0/month**, if you stay inside the limits below. Budget: ~2 hours the first time.
Limits were checked on 2026-10-05. Free tiers change, so re-check each provider's page.

## What runs where

| Component | Service | Free limit that matters |
| --- | --- | --- |
| Dev environment | GitHub Codespaces | 120 core-hours/month = ~60 h on a 2-core machine; 15 GB storage |
| CI/CD | GitHub Actions | Free for public repos |
| Business data (transactions, cases, audit) | Neon Postgres | 1 GB per project, 100 CU-hours/month, sleeps after 5 min idle |
| Entity graph | Neo4j AuraDB Free | 200k nodes, 400k relationships; **deleted after 30 days unused** |
| Kafka, Temporal, MLflow | Oracle Cloud Always Free VM (ARM) | **2 OCPU / 12 GB RAM**, 200 GB disk |
| Model artifacts | OCI Object Storage | 20 GB |
| Private network | Tailscale Personal | Free, 6 users |
| LLM (Step 4) | Gemini API free tier (Flash models) | Low rate limits; prompts may be used by Google, so synthetic data only |
| LLM tracing (Step 4) | Langfuse Cloud Hobby | 50k units/month, 30-day retention |
| Metrics, logs (Step 9) | Grafana Cloud Free | 10k series, 50 GB logs, 14-day retention |

> Oracle halved the Always Free ARM allowance in mid-2026 (from 4 OCPU/24 GB). Terraform here
> refuses to create anything larger than 2 OCPU/12 GB, so you can't be charged by accident.

## Accounts to create (in this order)

1. **GitHub**: create a **public** repo `aml-copilot` and push the code. Public = unlimited
   Actions minutes and protected environments for free, and it's your portfolio.
2. **Oracle Cloud** (cloud.oracle.com): sign up for Free Tier. Pick **Canada Southeast
   (Toronto)** as home region. Always Free resources exist only in the home region, and it
   can't be changed later.
3. **Tailscale** (tailscale.com): sign up with GitHub. First add the access policy below.
   Then in Settings -> Keys, create a **reusable** auth key with tag `tag:server` (for the VM),
   and in Settings -> OAuth clients, create a client with `Devices: write` scope and tag
   `tag:ci` (for GitHub Actions).
4. **Neon** (neon.tech): create project `aml`, Postgres 16, region AWS `ca-central-1`.
   Copy both connection strings: pooled (app) and direct (migrations).
5. **Neo4j Aura** (console.neo4j.io): create a Free instance. Save the password (shown once).
6. **Google AI Studio** (aistudio.google.com): create an API key. Needed from Step 4.
7. **Langfuse Cloud** and **Grafana Cloud**: create later (Steps 4 and 9).

## Tailscale access policy

In the Tailscale admin console -> Access controls, add these entries next to the existing
default rules (the default policy already allows network traffic between your devices):

```json
"tagOwners": { "tag:ci": ["autogroup:admin"], "tag:server": ["autogroup:admin"] },
"ssh": [
  { "action": "accept", "src": ["autogroup:member"], "dst": ["tag:server"], "users": ["ubuntu"] },
  { "action": "accept", "src": ["tag:ci"], "dst": ["tag:server"], "users": ["ubuntu"] }
]
```

Because the VM's auth key carries `tag:server`, it joins already tagged.

## Provision the VM

```bash
# 1. OCI API key: OCI console -> Profile -> API keys -> Add API key -> download private key
mkdir -p ~/.oci && mv ~/Downloads/*.pem ~/.oci/oci_api_key.pem && chmod 600 ~/.oci/oci_api_key.pem
# 2. SSH key if you don't have one
ssh-keygen -t ed25519
# 3. Fill in Terraform variables
cp infra/terraform/oci/terraform.tfvars.example infra/terraform/oci/terraform.tfvars
# 4. Create everything
make cloud-init && make cloud-plan && make cloud-apply
```

If `apply` fails with **"Out of host capacity"**, Oracle has no free ARM capacity in that
availability domain right now. Retry later (early morning works best), or change
`availability_domains[0]` to `[1]` or `[2]` in `main.tf` if your region has more than one.

Wait ~5 minutes for cloud-init, then check: `tailscale status` should list `aml-vm`.

## Object storage keys for MLflow

OCI console -> Profile -> **Customer secret keys** -> Generate. Put the access/secret key into
`OCI_S3_ACCESS_KEY` / `OCI_S3_SECRET_KEY`, and the `s3_compat_endpoint` Terraform output into
`MLFLOW_S3_ENDPOINT_URL`.

## Configure, migrate, deploy

```bash
cp .env.cloud.example .env.cloud     # fill in every value
make migrate                         # schema -> Neon
make cloud-deploy                    # Redpanda, Temporal, MLflow -> VM, then smoke tests
make data-synthetic && make cloud-load && make cloud-test-int
```

Service UIs (over Tailscale): Temporal http://aml-vm:8080 · MLflow http://aml-vm:5000 ·
Redpanda Console http://aml-vm:8081

## CI/CD secrets

GitHub repo -> Settings -> Environments -> new environment `production`
(optionally add yourself as required reviewer, like a bank change-approval gate). Add secrets:

| Secret | Value |
| --- | --- |
| `ENV_CLOUD` | Entire contents of `.env.cloud` |
| `AML_POSTGRES_MIGRATE_URL` | Neon direct connection string |
| `TS_OAUTH_CLIENT_ID`, `TS_OAUTH_SECRET` | Tailscale OAuth client |

Every push to `main` now runs: CI -> migrate Neon -> deploy to VM -> smoke test.

## Staying free

- The OCI budget alert emails you at the first cent of spend.
- Oracle reclaims an idle Always Free VM if CPU, network **and** memory all stay under 20% for
  7 days. The running stack uses ~40% of memory, so a live stack is safe. Don't stop it for weeks.
- AuraDB Free is deleted after 30 days unused. The graph is rebuilt from Postgres in Step 2,
  so losing it costs minutes, not data.
- Neon: business data only. Temporal's metadata stays on the VM because Temporal polls
  constantly and would keep Neon awake 24/7, burning the 100 CU-hours/month.
- Codespaces: stop your codespace when done (it auto-stops after 30 min idle by default).
- `make cloud-destroy` removes all Oracle resources if you ever want a clean slate.
