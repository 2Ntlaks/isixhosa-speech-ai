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
| R-0005 | 2026-10-17 | 3 | R-0004 model (NCHLT only) | none (evaluation) | FLEURS xh test, 1034 clips <= 30 s, all unseen | 94.86 | 29.81 | 0.03 | 0.03 | glues words: wrote 5 910 words for 16 703; 0 clips exact |
| R-0006 | 2026-10-17 | 3 | whisper-small (stock), sw tag forced | none (no training) | FLEURS xh test, 1034 clips | 185.34 | 65.45 | 0.05 | 0.04 | fair FLEURS baseline |
| R-0007 | 2026-10-17 | 3 | whisper-small fine-tuned, 4000 steps, sw tag | NCHLT train 51.2 h + FLEURS train 13.0 h (3 434 clips) | FLEURS xh test, 1034 clips | **44.38** | **10.16** | 2.37 | 1.90 | one change vs R-0004 (+FLEURS); word count now right (16 708 vs 16 703) |
| R-0007 | 2026-10-17 | 3 | (same model) | (same) | NCHLT xho test, 2770 clips | 16.80 | 2.91 | - | - | vs R-0004 16.63 / 2.98; unseen sentences WER 34.9 / CER 5.8 (R-0004: 36.6 / 6.2) |
| R-0008 | 2026-10-17 | 3 | whisper-medium smoke test (L4) | - | - | - | - | 0.25 | 0.20 | only fits with gradient checkpointing (17.4 GB, ~9 s/step); last check failed (P-0007) |
| R-0009 | 2026-10-17 | 3 | whisper-medium smoke test (L40S 48 GB) | - | - | - | - | 0.16 | 0.30 | FAILED: out of memory at batch 16 x 2 without checkpointing (P-0008) |
