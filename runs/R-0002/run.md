# R-0002 · Stage 2 smoke test: does the training pipeline work end to end?

- **Why:** before paying for 2-3 GPU hours, prove every part works on a tiny run: data download, training, checkpoint,
  resume after a restart, saving the final model, scoring it. Also measures seconds per step, so the full run's
  time and cost can be estimated from a real number instead of a guess. Also checks remote access (P-0002 fix).
- **Not a real model:** 40 steps is far too short to learn isiXhosa; its scores are not comparable to anything.
- **Command:** `cloud/run_job.sh --run R-0002 --max-hours 1 --market ondemand`
- **Expected:** both training parts finish, part 2 says "resuming from .../checkpoint-20", eval writes metrics.json.

## Attempt 1 · 2026-10-17 06:53 UTC · FAILED (commit a922e19)
- Data download fine (46 651 wav, 6.2 GB, ~6 min); split fine (42 269 train clips, 51.2 h, 195 speakers;
  dev speakers 005 023 066 077 173 192; 6 clips over 30 s dropped). Training crashed immediately:
  `ImportError: Using the Trainer with PyTorch requires accelerate>=0.26.0` (P-0005).
- Machine time ~8 min, about $0.11.
- Fix: accelerate==1.1.1 added to requirements-gpu.txt; new runs/preflight.sh (2 training steps on 4 speakers
  before the full download) so this class of error costs ~3 min instead of ~8.

## Attempt 2
(filled in after the run)
