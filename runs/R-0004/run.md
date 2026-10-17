# R-0004 · Stage 2: first fine-tune of whisper-small on NCHLT isiXhosa

- **Why:** the main stage 2 result. Teach Whisper isiXhosa from 51 h of speech by 195 speakers.
- **Compared with:** R-0003 (same model and tag, no training) and R-0001 (stock, language auto-detected).
- **What changes vs R-0003:** only the training. Same test set, same scoring (v1), same <|sw|> tag.
- **Command:** `cloud/run_job.sh --run R-0004 --max-hours 4 --market ondemand` (the node runs runs/R-0004/job.sh,
  which also runs R-0003 first).
- **Expected:** big drop in CER from R-0003; smaller drop on sentences never seen in training (the honest number).

## Outcome
(filled in after the run)
