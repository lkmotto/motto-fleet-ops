# AGENTS.md for motto-fleet-ops

## Overview
Merged fleet operations repository combining fleet provisioning tools (self-serve secret grants via Doppler to GitHub Actions) and burn rate tracking agent (monitors fleet burn rate with OTel + Langfuse observability).

## Development

### Setup
```bash
uv sync
```

### Run
```bash
uv run python -m provisioner
uv run python -m burn-rate
```

### Test
```bash
uv run pytest
```

### Lint
```bash
uv run ruff check .
```

### Type Check
```bash
uv run mypy .
```

## Deployment
Deployed via Docker to Northflank. Uses Maritime.sh for fleet management and Langfuse for observability.
