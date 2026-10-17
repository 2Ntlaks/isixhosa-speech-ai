# R-0009 · whisper-medium smoke test on an NVIDIA L40S (48 GB)

- **Why:** R-0008 showed medium only fits the 24 GB L4 with gradient checkpointing (~9 s/step). Decision D-0012: try a
  48 GB L40S (g6e.xlarge, $1.861/h) at batch 16 x 2 without checkpointing.
- **Command:** `FALLBACK_TYPES="" cloud/run_job.sh --run R-0009 --max-hours 1 --market ondemand --type g6e.xlarge`

## Outcome · 2026-10-17 · FAILED (commit 8679ea3, node i-06d622c5d8b4a2eb3)
- Preflight (whisper-small, 2 steps) 5.9 s vs 17.9 s on the L4: the L40S is ~3x faster.
- Speed test, medium, batch 16 x 2, no checkpointing:
  `torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 94.00 MiB. GPU 0 has a total capacity of 44.39 GiB of which 61.31 MiB is free.`
- The smoke test only tried that one set-up, so the job stopped (P-0008). Machine ~10 min, about $0.30.
- Follow-up: R-0010 tries both remaining set-ups and keeps the faster one that fits.
