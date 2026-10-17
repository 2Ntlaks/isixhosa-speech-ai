# R-0010 · Second whisper-medium smoke test on the L40S: try both remaining set-ups

- **Why:** R-0009 ran out of memory at batch 16 x 2 without checkpointing even with 48 GB. This run tries setup C
  (batch 16 x 2 + gradient checkpointing; known to fit on 24 GB) and setup B (batch 8 x 4, no checkpointing), keeps the
  faster one that fits, then runs the two-dev-set check, a medium checkpoint save/reload and the scoring-speed test.
- **Command:** `FALLBACK_TYPES="" cloud/run_job.sh --run R-0010 --max-hours 1 --market ondemand --type g6e.xlarge`
- **Cost:** about $0.40. Within the approved plan (smoke test, then the full-run cost goes to the founder).

## Outcome
(filled in after the run)
