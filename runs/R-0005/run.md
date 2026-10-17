# R-0005 · R-0004's model on the FLEURS isiXhosa test set

- **Why:** NCHLT test is short read prompts, 82 % of them sentences also in training. FLEURS test is 350 long natural
  sentences (avg 16 words, ~13 s) that appear in no training data at all: the first real check of how the stage 2 model
  copes with isiXhosa it has never rehearsed. No training; evaluation only.
- **Model:** s3://.../models/R-0004/ (whisper-small, 4000 steps on NCHLT, <|sw|>).
- **Test set:** FLEURS xh_za test, 1041 clips; the 7 over 30 s are left out (Whisper hears only 30 s) -> 1034 clips,
  all male speakers. max_new_tokens 225 (FLEURS sentences need up to 145 tokens).
- **Runs on:** the R-0007 node (runs/R-0007/job.sh). Outputs in S3 jobs/R-0005/out/.
- **Expected:** much worse than NCHLT's 3 % CER.

## Outcome · 2026-10-17 · DONE (R-0007 node i-07a2651bbc20319ef, commit 7e6acb3)
- **WER 94.86 %, CER 29.81 %, 0.0 % exact** on 1034 FLEURS test clips (7 over 30 s left out). All sentences unseen.
- Meaning: NCHLT-only training transfers the *sounds* (CER 65.5 -> 29.8 vs R-0006) but not word boundaries in long
  speech: the model wrote 5 910 words for 16 703 reference words, gluing phrases together (it only ever saw 3-word
  prompts). Median clip CER 25.3 %. Letter patterns written where the reference has them: kh 71 %, th 91 %, c 56 %.
- Cost: ~2 min of the R-0007 node, about $0.03.
