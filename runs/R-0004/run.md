# R-0004 · Stage 2: first fine-tune of whisper-small on NCHLT isiXhosa

- **Why:** the main stage 2 result. Teach Whisper isiXhosa from 51 h of speech by 195 speakers.
- **Compared with:** R-0003 (same model and tag, no training) and R-0001 (stock, language auto-detected).
- **What changes vs R-0003:** only the training. Same test set, same scoring (v1), same <|sw|> tag.
- **Command:** `cloud/run_job.sh --run R-0004 --max-hours 4 --market ondemand` (the node runs runs/R-0004/job.sh,
  which also runs R-0003 first).
- **Expected:** big drop in CER from R-0003; smaller drop on sentences never seen in training (the honest number).

## Outcome · 2026-10-17 · DONE (commit 51cd8ba, node i-0027134bed9c46ab2)
- Machine 07:31-09:50 UTC (~2.3 h, about $1.85). Training 7 581 s for 4000 steps (1.9 s/step including 8 dev evaluations
  and checkpoint saves; R-0002 measured 1.65 s/step for steps alone). GPU 100 % busy, 18 GB of 23 GB memory.
- Dev CER by checkpoint (600 clips, 6 speakers): 500: 7.03 · 1000: 6.31 · 1500: 4.45 · 2000: 4.09 · 2500: 3.73 ·
  3000: 3.61 · 3500: 3.63 · 4000: 3.53 (best, kept). Dev loss 0.465 -> 0.199. See loss.png.
- **Test (2770 clips, 8 unseen speakers): WER 16.63 %, CER 2.98 %, 64.51 % of clips exactly right.**
  - Sentences also in training (2259 clips): WER 12.1 %, CER 2.2 %, 72.7 % exact.
  - **Sentences never in training (511 clips): WER 36.6 %, CER 6.2 %, 28.2 % exact.** The honest headline.
  - Per speaker CER: 500 1.3, 501 1.2, 502 4.1, 503 0.6, 504 3.0, 505 6.9, 506 4.5, 507 2.4. Women 3.2, men 2.8.
- vs R-0003 (same tag, no training): CER 45.70 -> 2.98, WER 164.46 -> 16.63. Letter patterns now written where the
  reference has them: kh 96.7 %, th 98.8 %, hl 98.3 %, dl 97.5 %, x 94.0 %, q 94.5 % (comparison.json).
- Remaining errors: 983 clips not exact; 720 of them have CER <= 10 % (one small slip, e.g. umnumzana -> umnomzana);
  only 34 are pure word-boundary errors. Worst clips include unusual prompts mixing English (kwe draw nganye, art ubethe zesize).
- Overfitting signal: training loss drops in a step at the start of each pass over the data (steps ~1320, ~2640) while dev
  loss only eases down; dev CER plateaued from step 3000. ~3 passes is about the limit for this data and model size.
- Model: s3://mgaguli-studio-render-<acct>/models/R-0004/ (model.safetensors, 967 MB, plus processor files).
- Visibility issue during the run: P-0006 (progress lines buffered by grep).
