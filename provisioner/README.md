# motto-fleet-provisioner

Self-serve credential provisioning for Factory Droids (and any fleet agent).

## How it works

1. Factory (or any agent / human) opens an issue in **any repo under `lkmotto/motto-*`** with title prefix `[provision]` and a body listing the secrets it needs.
2. A repository_dispatch webhook fires this repo's `provision.yml` workflow.
3. The workflow reads requested keys from Doppler `motto-core/prd`, sets them as GitHub Actions secrets on the target repo, and comments back on the issue with confirmation.
4. The agent re-runs whatever it was doing — secrets are now available to its workflow.

## Mode

**Full self-serve** (per Luke's decision 2026-05-10). No human gate. Factory can grant itself anything in `motto-core/prd`.

If a request asks for a key that does NOT exist in Doppler, the workflow comments back with an error and lists the closest matches.

## Request format

Open an issue in the target repo:

```
Title: [provision] <repo-name> needs <reason>
Body:
secrets:
  - DEEPSEEK_API
  - APOLLO_API_KEY
  - RESEND_API_KEY
reason: bringing motto-X back online, MOT-NN
```

## Audit trail

Every provision event:
- Comments on the originating issue with the secret names provisioned (never the values)
- Logs to `audit/provision-log.jsonl` in this repo (one line per request)
- Posts to Discord webhook `FLEET_PROVISION_WEBHOOK` if configured

## Required repo secrets in this provisioner

| Secret | Purpose |
|---|---|
| `DOPPLER_TOKEN` | Service token with read-only access to motto-core/prd |
| `FLEET_PROVISION_PAT` | GitHub PAT with `repo` scope across all motto-* repos |
| `FLEET_PROVISION_WEBHOOK` | Optional Discord webhook for audit pings |

## Triggers

- **Workflow dispatch:** manual via GitHub UI for testing
- **Repository dispatch event** `provision-request`: fired by a tiny shim workflow in each motto-* repo when a `[provision]` issue is opened
- **Issue opened on this repo** with title prefix `[provision]`: direct path

See `.github/workflows/provision.yml` for the implementation.
