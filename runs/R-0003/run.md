# R-0003 · Stock whisper-small with the Swahili tag forced (no training)

- **Why:** R-0002 hinted that most of the early improvement comes from forcing the <|sw|> tag, not from training.
  This run measures that, so stage 2's real gain is measured against a fair baseline.
- **What changes vs R-0001:** only the language: forced <|sw|> instead of auto-detect. No training.
- **Runs on:** the same node as R-0004, before training (runs/R-0004/job.sh). Outputs: jobs/R-0003/out/ in S3.
- **Command:** see runs/R-0004/run.md.

## Outcome · 2026-10-17 · DONE (node of R-0004, commit 51cd8ba)
- **WER 164.46 %, CER 45.7 %** on all 2770 test clips (R-0001 with auto-detect: WER 196.56, CER 75.09).
- Seen sentences: CER 42.7 %; unseen: CER 58.0 % (no training, so the gap is sentence difficulty, not memorisation).
- Per speaker CER: 500 38.0, 501 42.7, 502 34.3, 503 46.8, 504 44.0, 505 37.2, 506 72.1, 507 39.6. Speaker 506 is an outlier.
- Meaning: forcing the tag alone removes the wrong-language / wrong-script failures (75 -> 46 % CER). It still spells
  isiXhosa like Swahili: kh written in 1.2 % of the places it should be, th 0.9 %, x 0.4 % (runs/R-0004/comparison.json).
- Transcription took 140 s. Cost: ~3 min of the R-0004 machine, about $0.03.
