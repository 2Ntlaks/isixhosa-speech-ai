# R-0005 · R-0004's model on the FLEURS isiXhosa test set

- **Why:** NCHLT test is short read prompts, 82 % of them sentences also in training. FLEURS test is 350 long natural
  sentences (avg 16 words, ~13 s) that appear in no training data at all: the first real check of how the stage 2 model
  copes with isiXhosa it has never rehearsed. No training; evaluation only.
- **Model:** s3://.../models/R-0004/ (whisper-small, 4000 steps on NCHLT, <|sw|>).
- **Test set:** FLEURS xh_za test, 1041 clips; the 7 over 30 s are left out (Whisper hears only 30 s) -> 1034 clips,
  all male speakers. max_new_tokens 225 (FLEURS sentences need up to 145 tokens).
- **Runs on:** the R-0007 node (runs/R-0007/job.sh). Outputs in S3 jobs/R-0005/out/.
- **Expected:** much worse than NCHLT's 3 % CER.

## Outcome
(filled in after the run)
