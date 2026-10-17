# R-0002 · Stage 2 smoke test: does the training pipeline work end to end?

- **Why:** before paying for 2-3 GPU hours, prove every part works on a tiny run: data download, training, checkpoint,
  resume after a restart, saving the final model, scoring it. Also measures seconds per step, so the full run's
  time and cost can be estimated from a real number instead of a guess. Also checks remote access (P-0002 fix).
- **Not a real model:** 40 steps is far too short to learn isiXhosa; its scores are not comparable to anything.
- **Command:** `cloud/run_job.sh --run R-0002 --max-hours 1 --market ondemand`
- **Expected:** both training parts finish, part 2 says "resuming from .../checkpoint-20", eval writes metrics.json.

## Outcome
(filled in after the run)
