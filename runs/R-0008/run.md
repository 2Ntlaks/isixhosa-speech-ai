# R-0008 · Smoke test for whisper-medium (speed, memory, new two-dev-set evaluation)

- **Why:** whisper-medium has 769M parameters (3x whisper-small). Before the full run, measure on the L4 (24 GB):
  does training fit at batch 16 x 2 (A), batch 8 x 4 (B), or batch 16 x 2 with gradient checkpointing (C)? Seconds per
  step for each, peak GPU memory, checkpoint size, scoring speed. Also tests the FLEURS dev set added as a second,
  information-only dev check (best checkpoint still chosen on NCHLT dev, as in R-0004 and R-0007).
- **Decision:** D-0011 (founder: "yes go with whisper-medium").
- **Command:** `cloud/run_job.sh --run R-0008 --max-hours 1 --market ondemand`
- **Not a real model.** The full-run cost estimate goes to the founder before the full run starts.

## Outcome
(filled in after the run)
