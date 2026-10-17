# R-0006 · Stock whisper-small with <|sw|> forced, on the FLEURS isiXhosa test set

- **Why:** the fair FLEURS baseline (the FLEURS twin of R-0003), so R-0005 and R-0007 can be judged against "no training".
- **Test set and settings:** as R-0005. Runs on the R-0007 node. Outputs in S3 jobs/R-0006/out/.

## Outcome · 2026-10-17 · DONE (R-0007 node i-07a2651bbc20319ef, commit 7e6acb3)
- **WER 185.34 %, CER 65.45 %, 0.0 % exact** on 1034 FLEURS test clips (7 over 30 s left out). All sentences unseen.
- Meaning: the FLEURS baseline with no training. Wrote 31 832 words for 16 703 (splits words into syllables), Swahili-style
  spelling (kh 1.6 %, th 2.2 % of reference occurrences written).
- Cost: ~3 min of the R-0007 node, about $0.04.
