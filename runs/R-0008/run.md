# R-0008 · Smoke test for whisper-medium (speed, memory, new two-dev-set evaluation)

- **Why:** whisper-medium has 769M parameters (3x whisper-small). Before the full run, measure on the L4 (24 GB):
  does training fit at batch 16 x 2 (A), batch 8 x 4 (B), or batch 16 x 2 with gradient checkpointing (C)? Seconds per
  step for each, peak GPU memory, checkpoint size, scoring speed. Also tests the FLEURS dev set added as a second,
  information-only dev check (best checkpoint still chosen on NCHLT dev, as in R-0004 and R-0007).
- **Decision:** D-0011 (founder: "yes go with whisper-medium").
- **Command:** `cloud/run_job.sh --run R-0008 --max-hours 1 --market ondemand`
- **Not a real model.** The full-run cost estimate goes to the founder before the full run starts.

## Outcome · 2026-10-17 · FAILED at the last part (commit 8ceaec1, node i-00c18b4f7a7d939fa)
- Setup A (batch 16 x 2): `torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 94.00 MiB. GPU 0 has a total capacity of 22.04 GiB of which 35.12 MiB is free.`
- Setup B (batch 8 x 4): out of memory too (same message, 48 MiB).
- **Setup C (batch 16 x 2, gradient checkpointing): fits, peak 17.41 GB, 188 s for 20 steps (~9 s/step).**
  4000 steps would take ~10 h on the L4 (~$8.50) and exceed the 6 h cap.
- Two-dev-set check: out of memory, because it used batch 8 x 4 without checkpointing (my mistake, P-0007); job stopped
  (set -e), so the scoring-speed test did not run.
- Why medium doesn't fit: weights + gradients + Adam's two running averages, all fp32, are ~12 GB before any audio.
- Machine ~15 min, about $0.20.
- Founder chose (D-0012) to retry on a 48 GB NVIDIA L40S (g6e.xlarge): smoke test R-0009.
