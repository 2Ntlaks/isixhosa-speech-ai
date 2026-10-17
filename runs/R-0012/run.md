# R-0012 · Stage 3, experiment 2: whisper-medium on NCHLT + FLEURS

- **Why:** R-0007 (whisper-small) is the best model so far (FLEURS CER 10.16, NCHLT CER 2.91). A 3x larger model
  usually gives the biggest single gain (D-0011).
- **One change vs R-0007:** openai/whisper-medium (769M parameters) instead of whisper-small (244M). Same data, same 6
  dev speakers, 4000 steps x 32 clips, lr 1e-5, warmup 500, linear decay, bf16, best checkpoint on NCHLT dev CER.
- **Not a change in the recipe, forced by memory:** 32 clips per step are reached as 8 x 4 (gradient accumulation)
  instead of 16 x 2; the update per step is the same average over 32 clips. Set-up measured in R-0010: 32.8 GB peak,
  2.76 s/step on the L40S (P-0008).
- **Added, information only:** 200 FLEURS dev clips scored at each evaluation (R-0007's lesson: NCHLT-only dev hid the
  FLEURS gain). Selection stays on NCHLT dev. Caveat: dev evaluation uses max 96 output tokens (as R-0007, so NCHLT dev
  stays comparable), which can cut off the longest FLEURS dev sentences; FLEURS dev CER is therefore a slight
  overestimate. The FLEURS test score uses 225 tokens as before.
- **Also on this node:** R-0011 (stock medium baseline) first, ~10 min.
- **Checkpoints** (8.6 GB each) stay on the node (`model/`, outside `out/`), so the 5-minute S3 sync does not copy
  ~70 GB of checkpoints nobody uses. Final model to s3://mgaguli-studio-render-<acct>/models/R-0012/.
- **Command:** `DISK_GB=200 FALLBACK_TYPES="" cloud/run_job.sh --run R-0012 --type g6e.xlarge --market ondemand --max-hours 6`
- **Founder approval:** 2026-10-17, "tell me when it's done" in reply to the plan (~3.7 h, ~$7) (D-0013).
- **Expected:** FLEURS test CER clearly below R-0007's 10.16; NCHLT test not worse than 2.91. Est. ~3.7 h, ~$7, cap 6 h.
