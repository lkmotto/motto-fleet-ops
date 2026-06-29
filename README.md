# motto-fleet-ops

Merged fleet operations repository combining two previously standalone repos:

- **provisioner/** — formerly [motto-fleet-provisioner](https://github.com/lkmotto/motto-fleet-provisioner) (archived). Self-serve secret grants via Doppler → GitHub Actions secrets.
- **burn-rate/** — formerly [motto-fleet-burn-rate-tracker](https://github.com/lkmotto/motto-fleet-burn-rate-tracker) (archived). Agent that monitors fleet burn rate with OTel + Langfuse observability.

## Structure

```
motto-fleet-ops/
  provisioner/       # Fleet provisioning tools
  burn-rate/         # Burn rate tracking agent
```

## History

This repo was created by merging the two source repos using `git merge --allow-unrelated-histories` with full history preservation. Each source repo's files were moved into their respective subdirectories before merging.
