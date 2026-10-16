# R-0001 · Stage 1 baseline: stock whisper-small on NCHLT isiXhosa test

- **Why:** the "before" number. Whisper has never been taught isiXhosa; every later run is compared to this.
- **What changes vs previous run:** nothing (first run).
- **Decision:** D-0006 (run stage 1 in the cloud on the full test set; language auto-detected).
- **Command:** `cloud/run_job.sh --run R-0001 --max-hours 1` (node runs `runs/R-0001/job.sh`)
- **Expected:** WER above 80 %; Whisper will label the clips as some other language.

## Outcome
(filled in after the run)
