# R-0011 · Stage 3, experiment 2 baseline: stock whisper-medium + <|sw|>

- **Why:** the fair "before" score for R-0012. Stock small + tag scored NCHLT CER 45.70 (R-0003) and FLEURS CER 65.45
  (R-0006); this measures how much the bigger stock model already knows before any isiXhosa training.
- **What:** openai/whisper-medium, no training, <|sw|> forced. NCHLT test (2770 clips, max 96 output tokens, as R-0003)
  and FLEURS test (clips <= 30 s, max 225 tokens, as R-0006). Same evaluator and normalisation v1.
- **Command:** runs on the R-0012 node (`runs/R-0012/job.sh`, `cloud/run_job.sh --run R-0012 ...`); outputs synced to
  s3://mgaguli-studio-render-<acct>/jobs/R-0011/out/.
- **Founder approval:** 2026-10-17, part of the R-0012 run (D-0013).
