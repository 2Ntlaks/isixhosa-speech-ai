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

## Outcome · 2026-10-17 · DONE (commit 3049bd7, node i-0b595f558779a6d69)
- Launch: no g6e.xlarge capacity in any us-east-1 zone at 15:1x UTC (P-0009); a retry loop got one at 15:22 UTC.
- Machine 15:22-17:42 UTC, ~2.33 h at $1.861/h, about $4.34 in total (R-0012 itself ~$3.90). Estimate was ~3.7 h /
  ~$7: the real training speed was 1.52 s/step, not R-0010's 2.76 (that figure included start-up in only 30 steps).
- Training 7 232 s for 4000 steps (1.81 s/step incl. evaluations); peak GPU memory 33.35 GB of 48.
- Data identical to R-0007: 45 703 clips, 64.23 h (NCHLT 42 269 + FLEURS 3 434), 196 training speakers.
- Dev CER (NCHLT, same 600 clips as R-0004/R-0007): 500: 5.92 · 1000: 4.32 · 1500: 3.57 · 2000: 3.19 · 2500: 2.93 ·
  3000: 2.75 · 3500: 2.82 · **4000: 2.66 (best, kept)**. R-0007: 3.74. See loss.png.
- FLEURS dev CER (200 clips, information only, max 96 tokens): 13.42 · 10.40 · 8.56 · 8.84 · 7.98 · 7.99 · 8.02 · 7.79.
- **FLEURS test (1034 clips, all unseen sentences): WER 37.83 %, CER 8.03 %** (R-0007: 44.38 / 10.16).
  Median clip CER 6.77 % (R-0007 8.73); 345 clips under 5 % (R-0007 213); 26 clips at 20 % or worse (R-0007 62).
  Clip by clip vs R-0007: 698 better, 233 worse, 103 the same. Words written 16 932 for 16 703 (R-0007 16 708).
  Clips with digits in the reference (200): CER 8.56 (R-0007 12.75); without digits (834): 7.89 (R-0007 9.49).
- **NCHLT test (2770 clips): WER 12.71 %, CER 2.33 %, 71.5 % exact** (R-0007: 16.80 / 2.91 / 64.4).
  Seen sentences WER 9.0 / CER 1.7 (R-0007 12.7 / 2.2); **unseen WER 28.7 / CER 5.0 (R-0007 34.9 / 5.8)**.
  Clip by clip vs R-0007: 457 better, 208 worse, 2105 the same.
- Click and letter-pattern recall on FLEURS (share of reference occurrences reproduced): q 98.1, x 97.2, c 83.7, kh 90.9
  (R-0007: 97.9, 96.0, 81.3, 89.0).
- Conclusion: the bigger model is better on every measure, on both test sets: about 20 % fewer letter errors (FLEURS
  10.16 -> 8.03, NCHLT 2.91 -> 2.33) and 15-24 % fewer word errors, for ~$3.90. English loanwords and names
  (nuclear, radioactive caesium, Gibson) are still the main misses. R-0012 is the best model so far.
- Model: s3://mgaguli-studio-render-<acct>/models/R-0012/ (3.06 GB). Checkpoints were not kept (node disk only).
  Comparisons: comparison_fleurs.json, comparison_nchlt.json (with R-0007, R-0011 and the stock-small baselines).
