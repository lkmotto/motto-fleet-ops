# CI Investigation — MOT-31

## What's failing

All GitHub Actions workflow runs are failing with the same error:

> **"The job was not started because recent account payments have failed or your spending limit needs to be increased. Please check the 'Billing & plans' section in your settings."**

This affects every workflow in the repository:

| Workflow | Trigger | Status |
|---|---|---|
| `release-please` | push to `main` | failure — billing block |
| `Dependabot auto-merge` | PR from `dependabot[bot]` | failure — billing block |
| `provision` | issue / dispatch | would also block |

## What I tried

1. **Inspected `gh run list --limit 20`** — confirmed all recent runs on `main` are `failure`.
2. **Queried the GitHub API** for check-run annotations (`/repos/*/check-runs/*/annotations`) — revealed the exact billing/payment failure message.
3. **Attempted to download logs** via `gh run download` — no log artifacts available (jobs never started).
4. **Ran `ruff check` and `ruff format` locally** — found and fixed one lint error (E401 — multiple imports on one line) and formatting issues across 3 Python files. These are secondary; the primary blocker is the billing block.
5. **Ran `pre-commit run --all-files`** — fixed a missing trailing newline (end-of-file-fixer).

## What a human needs to do

1. **Resolve the GitHub billing issue:**
   - Go to **GitHub → Settings → Billing & plans** for the `lkmotto` account.
   - Update the payment method or increase the spending limit so that GitHub Actions runners can start again.
2. **Re-run the failed workflows** once billing is resolved (or push a trivial commit to `main` to trigger `release-please` again).
