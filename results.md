# Results

Every experiment, including bad and failed ones. One row per run; details live in `runs/<RUN-ID>/`.
Scores are on the fixed held-out test set named in the row. Never delete a row. Numbers in the write-up must cite a run ID.

| Run | Date | Stage | Model | Training data | Test set | WER % | CER % | GPU h | Cost $ | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| R-0001 | 2026-10-16 | 1 | whisper-small (stock) | none (no training) | NCHLT xho test, 2770 clips, 8 spk | 196.56 | 75.09 | 0.16 | 0.13 | language auto-detected (52 languages, 32% Swahili); 30% non-Latin output; 22 exact matches, all English prompts |
