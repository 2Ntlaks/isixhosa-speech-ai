# Results

Every experiment, including bad and failed ones. One row per run; details live in `runs/<RUN-ID>/`.
Scores are on the fixed held-out test set named in the row. Never delete a row. Numbers in the write-up must cite a run ID.

| Run | Date | Stage | Model | Training data | Test set | WER % | CER % | GPU h | Cost $ | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| R-0001 | 2026-10-16 | 1 | whisper-small (stock) | none (no training) | NCHLT xho test, 2770 clips, 8 spk | 196.56 | 75.09 | 0.16 | 0.13 | language auto-detected (52 languages, 32% Swahili); 30% non-Latin output; 22 exact matches, all English prompts |
| R-0002 (attempt 1) | 2026-10-17 | 2 | whisper-small | smoke test | - | - | - | 0.13 | 0.11 | FAILED: missing `accelerate` package (P-0005); retried as attempt 2 |
| R-0002 (attempt 2) | 2026-10-17 | 2 | whisper-small, 40 steps (smoke) | NCHLT train, 195 spk | NCHLT test, first 300 clips (spk 500 only) | 77.47 | 16.75 | 0.20 | 0.16 | pipeline check only, not comparable; 1.65 s/step |
| R-0003 | 2026-10-17 | 2 | whisper-small (stock), <\|sw\|> forced | none (no training) | NCHLT xho test, 2770 clips, 8 spk | 164.46 | 45.70 | 0.04 | 0.03 | fair baseline for stage 2; seen CER 42.7 / unseen 58.0 |
| R-0004 | 2026-10-17 | 2 | whisper-small fine-tuned, 4000 steps, <\|sw\|> | NCHLT train, 195 spk, 51.2 h | NCHLT xho test, 2770 clips, 8 spk | 16.63 | 2.98 | 2.30 | 1.85 | best = step 4000 (dev CER 3.53); seen WER 12.1 / CER 2.2; **unseen WER 36.6 / CER 6.2**; 64.5 % clips exact |
