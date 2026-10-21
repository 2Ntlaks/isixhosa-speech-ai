# R-0018 · R-0012's model on the Swivuriso test set (the "before" for R-0019)

- **What:** R-0012 (whisper-medium, NCHLT + FLEURS) scored on Swivuriso dev_test: clips 1-30 s without [?], own
  speakers, max 440 output tokens. Includes a scripted (read) vs unscripted (own words) breakdown.
- **Why:** R-0019 adds Swivuriso; this is the score to beat, and shows how Thetha copes with natural speech today.
- **Runs on the R-0019 node** (runs/R-0019/job.sh), output in s3://<bucket>/jobs/R-0018/out/.

## Outcome · 2026-10-21 · DONE (on the R-0019 node)
- Swivuriso test, 2145 clips, 9.4 h, 24 speakers: **WER 37.32 %, CER 9.00 %**, exact 6.3 %.
- Read (scripted) 1422 clips: 33.4 / 7.6. **Unscripted (own words) 723 clips: 42.4 / 10.8**: today's Thetha struggles
  most with natural speech, as expected from reading-only training.
