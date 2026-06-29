# AGENTS.md

> Operational spec for autonomous coding agents (Factory Droid, Codex, Cursor, Aider).

## Identity
- **Repo:** `lkmotto/motto-fleet-provisioner`
- **Purpose:** Self-serve credential provisioning lane for the motto agent fleet. Factory requests secrets via issue, workflow grants them, no human gate.
- **Status:** active
- **Owner:** Luke Motto (`ljm32901@gmail.com`)
- **Linear team:** Mottoappraisal (MOT) · project Fleet Operations

## What this code does

When any agent (Factory most often) needs a secret to run a job, it opens an issue with `[provision]` title prefix listing the secrets needed. This repo's workflow reads them from Doppler `motto-core/prd`, sets them as GitHub Actions secrets in the target repo, and comments back. Self-serve. No human in the loop. Audit trail in `audit/provision-log.jsonl`.

## Architecture at a glance
- `.github/workflows/provision.yml` — main provisioning workflow
- `.github/workflows/dispatch-shim.yml` — installed in each target repo, fires `repository_dispatch` to this repo when a `[provision]` issue opens
- `scripts/grant_secrets.sh` — Doppler → GitHub secret set logic
- `scripts/append_audit.py` — appends to audit log
- `audit/provision-log.jsonl` — durable audit trail (one JSON line per request)

## Runtime
- **Language/runtime:** bash + python 3.11 in GitHub Actions
- **Entry point:** GitHub Actions (no local runtime)
- **Hosting:** GitHub-hosted runners
- **Schedule:** event-driven (issue open / repo dispatch)

## Required environment variables
| Variable | Purpose | Source |
|---|---|---|
| `DOPPLER_TOKEN` | Service token with read access to motto-core/prd | Doppler service token |
| `FLEET_PROVISION_PAT` | GitHub PAT with `repo` scope across `lkmotto/motto-*` | Manual issuance |
| `FLEET_PROVISION_WEBHOOK` | Discord webhook for audit pings | Optional |

## Conventions
- DeepSeek V4 / Reasoner only for code changes. No Claude.
- One PR per change. Audit log is append-only — never edit history.
- The provisioner is the ONLY system with write access to motto-* repo secrets via PAT. Treat its credentials accordingly.

## Known issues / open loops
- PAT rotation is manual today. Add quarterly rotation reminder.
- No allowlist of secret names; Factory can request any key in motto-core/prd. This is intentional (full self-serve) — if abused, narrow it later.
