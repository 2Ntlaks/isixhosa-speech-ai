# R-0010 · Second whisper-medium smoke test on the L40S: try both remaining set-ups

- **Why:** R-0009 ran out of memory at batch 16 x 2 without checkpointing even with 48 GB. This run tries setup C
  (batch 16 x 2 + gradient checkpointing; known to fit on 24 GB) and setup B (batch 8 x 4, no checkpointing), keeps the
  faster one that fits, then runs the two-dev-set check, a medium checkpoint save/reload and the scoring-speed test.
- **Command:** `FALLBACK_TYPES="" cloud/run_job.sh --run R-0010 --max-hours 1 --market ondemand --type g6e.xlarge`
- **Cost:** about $0.40. Within the approved plan (smoke test, then the full-run cost goes to the founder).

## Outcome · 2026-10-17 · DONE (commit f91cdbe, node i-09d9ecea758779aae, 13:34-13:50 UTC, about $0.50)
- Setup C (batch 16 x 2 + gradient checkpointing): fits, peak 17.41 GB, 3.27 s/step (30 steps incl. start-up).
- **Setup B (batch 8 x 4, no checkpointing): fits, peak 32.75 GB, 2.76 s/step. Chosen.**
- Two-dev-set evaluation works: eval_nchlt_cer 24.97 -> 23.19 and eval_fleurs_cer 36.67 -> 34.16 at steps 2 and 4;
  best checkpoint chosen on NCHLT (checkpoint-4). Medium checkpoint: 8.6 GB; saves and reloads OK.
- Scoring speed: stock whisper-medium + sw tag, 200 FLEURS test clips in 33 s (on those 200 clips CER 48.29, WER 142.19;
  a subset, not comparable with full-test numbers).
- Disk after data and caches: 26 GB free of 96 GB. A full run keeps 2 checkpoints and briefly writes a third
  (~26 GB): too tight, so the full run uses a 200 GB disk (DISK_GB in cloud/run_job.sh).
- Note: the watcher (Monitor) reported nothing after the start although the job finished DONE at 13:49; found by
  reading the log directly. Watch future runs over SSM as well.
