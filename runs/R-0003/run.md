# R-0003 · Stock whisper-small with the Swahili tag forced (no training)

- **Why:** R-0002 hinted that most of the early improvement comes from forcing the <|sw|> tag, not from training.
  This run measures that, so stage 2's real gain is measured against a fair baseline.
- **What changes vs R-0001:** only the language: forced <|sw|> instead of auto-detect. No training.
- **Runs on:** the same node as R-0004, before training (runs/R-0004/job.sh). Outputs: jobs/R-0003/out/ in S3.
- **Command:** see runs/R-0004/run.md.

## Outcome
(filled in after the run)
