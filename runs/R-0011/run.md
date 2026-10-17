# R-0011 · Stage 3, experiment 2 baseline: stock whisper-medium + <|sw|>

- **Why:** the fair "before" score for R-0012. Stock small + tag scored NCHLT CER 45.70 (R-0003) and FLEURS CER 65.45
  (R-0006); this measures how much the bigger stock model already knows before any isiXhosa training.
- **What:** openai/whisper-medium, no training, <|sw|> forced. NCHLT test (2770 clips, max 96 output tokens, as R-0003)
  and FLEURS test (clips <= 30 s, max 225 tokens, as R-0006). Same evaluator and normalisation v1.
- **Command:** runs on the R-0012 node (`runs/R-0012/job.sh`, `cloud/run_job.sh --run R-0012 ...`); outputs synced to
  s3://mgaguli-studio-render-<acct>/jobs/R-0011/out/.
- **Founder approval:** 2026-10-17, part of the R-0012 run (D-0013).

## Outcome · 2026-10-17 · DONE (commit 3049bd7, node i-0b595f558779a6d69, g6e.xlarge L40S)
- Ran 15:24-15:37 UTC on the R-0012 node (incl. setup and data), ~0.25 h, about $0.45.
- **NCHLT test (2770 clips): WER 137.21 %, CER 33.74 %**, 1.44 % exact; seen sentences 133.9 / 32.5, unseen 151.6 / 38.9.
  Stock small + tag (R-0003): 164.46 / 45.70.
- **FLEURS test (1034 clips <= 30 s, 7 longer left out): WER 142.32 %, CER 45.86 %**, 0 % exact.
  Stock small + tag (R-0006): 185.34 / 65.45.
- Scoring speed: 122 s for NCHLT test, 149 s for FLEURS test.
- Conclusion: before any isiXhosa training, medium already makes about a quarter (NCHLT) to a third (FLEURS) fewer letter
  errors than small, but it is still unusable: it hears isiXhosa as Swahili-like syllables (clicks: q 0 %, x 0.7 %
  of reference occurrences reproduced on NCHLT).
