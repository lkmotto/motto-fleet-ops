# AGENTS.md

> Operational spec for autonomous coding agents (Factory Droid, Codex, Cursor, Aider). Human-readable too.

## Identity
- **Repo:** `lkmotto/motto-fleet-burn-rate-tracker`
- **Purpose:** Daily fleet cost aggregation and burn rate reporting agent that pulls spending data from `motto-finance-tracker` and Supabase to analyze operational costs.
- **Status:** Dark since 2026-04-01 — likely never fully deployed; minimal code scaffolding
- **Owner:** Luke Motto (`ljm32901@gmail.com`)
- **Linear team:** Mottoappraisal (MOT) · project Fleet Operations

## What this code does
Python agent that calls the `motto-finance-tracker` REST API (on Render) and Supabase to aggregate daily fleet operational spend, computes burn rate metrics using LangChain + OpenAI, and reports findings. Downstream consumers: Luke Motto (manual review) and potentially Telegram fleet chat.

## Architecture at a glance
- `agent/agent.py` — Core agent: fetches data from finance tracker + Supabase, runs burn rate analysis, reports
- `agent/__init__.py` — Package init
- `Dockerfile` — Container build
- `requirements.txt` — Python deps (supabase, langchain, openai, pandas, APScheduler, requests)

## Runtime
- **Language/runtime:** Python 3.x
- **Entry point:** `python -m agent` or `python agent/agent.py`
- **Hosting:** Not deployed — no Northflank/Maritime/Render config present
- **Schedule:** `manual` or scheduled cron (APScheduler in deps, no schedule configured)

## Required environment variables
| Variable | Purpose | Source |
|---|---|---|
| `SUPABASE_URL` | Supabase project URL for cost data | Doppler `motto-core/prd` |
| `SUPABASE_KEY` | Supabase service role key | Doppler `motto-core/prd` |
| `MOTTO_FINANCE_API_URL` | `motto-finance-tracker` REST API base URL (default: `https://motto-finance-tracker.onrender.com/api`) | Northflank env |
| `MOTTO_FINANCE_API_KEY` | Auth key for finance tracker API | Doppler `motto-core/prd` |
| `OPENAI_API_KEY` | LangChain/OpenAI for burn rate analysis | Doppler `motto-core/prd` |
| `MAX_COST_PER_RUN` | Cost cap per run in USD (default: 5.0) | Northflank env |
| `AGENT_NOTIFICATION_EMAIL` | Email for alert notifications (optional) | Northflank env |

## Doppler config
- Project: `motto-core`
- Config: `prd`
- Pull command: `doppler run --project motto-core --config prd -- <command>`

## How to run locally
```bash
pip install -r requirements.txt
# Set env vars then:
python agent/agent.py
```

## How to deploy
No deploy pipeline. Needs Northflank cron job or scheduled container run to be useful. `Dockerfile` is present but no CI/CD configured.

## Conventions
- Branch from `main`. PRs only. No direct pushes to main.
- Use DeepSeek V4 / Reasoner for code generation. Claude is banned from this fleet for cost reasons.
- One PR per logical change. Keep diffs minimal.
- Update this AGENTS.md if you change the architecture.

## Known issues / open loops
- No `.env.example` — env vars inferred from code.
- Uses OpenAI (not DeepSeek/Groq) — costs money on every run; consider switching LLM provider.
- Depends on `motto-finance-tracker` being live on Render.
- `fleet_reporter` import (`from fleet_reporter import report_action`) references a missing package — will fail at import unless installed separately.
- No deploy pipeline — investigate before relying on this for production burn rate data.

## Maritime status
Maritime.sh is dead. This repo does not reference Maritime.
