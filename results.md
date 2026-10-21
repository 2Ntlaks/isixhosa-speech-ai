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
| R-0010 | 2026-10-17 | 3 | whisper-medium smoke test (L40S) | - | - | - | - | 0.27 | 0.50 | batch 8 x 4 fits (32.8 GB), 2.76 s/step; checkpoint 8.6 GB; two-dev-set eval works |
| R-0011 | 2026-10-17 | 3 | whisper-medium (stock), sw tag forced | none (no training) | NCHLT xho test, 2770 clips | 137.21 | 33.74 | 0.25 | 0.45 | fair medium baseline (small: 164.46 / 45.70); seen CER 32.5 / unseen 38.9 |
| R-0011 | 2026-10-17 | 3 | (same model) | (same) | FLEURS xh test, 1034 clips | 142.32 | 45.86 | - | - | small: 185.34 / 65.45 |
| R-0012 | 2026-10-17 | 3 | whisper-medium fine-tuned, 4000 steps, sw tag | NCHLT train 51.2 h + FLEURS train 13.0 h (same as R-0007) | FLEURS xh test, 1034 clips | **37.83** | **8.03** | 2.08 | 3.89 | one change vs R-0007 (model size); L40S, batch 8 x 4; best checkpoint step 4000 (dev CER 2.66) |
| R-0012 | 2026-10-17 | 3 | (same model) | (same) | NCHLT xho test, 2770 clips | **12.71** | **2.33** | - | - | vs R-0007 16.80 / 2.91; unseen sentences WER 28.7 / CER 5.0 (R-0007 34.9 / 5.8) |
| R-0013 | 2026-10-17 | 3 | R-0012 as CTranslate2 int8 (laptop CPU) | (same as R-0012) | NCHLT xho test, 200 unseen-sentence clips | 31.74 | 5.67 | 0 | 0 | same clips on GPU fp16: 31.06 / 5.69; 186/200 outputs identical; 6-7 s per clip on the laptop CPU |
| R-0014 | 2026-10-19 | 4 | R-0007 as CTranslate2 int8 (laptop CPU), sw tag | (same as R-0007) | Soapies engxho test (code-switched TV speech), 391 clips | 87.97 | 42.13 | 0 | 0 | English words right 17 %, isiXhosa 12 %; research-only test set (D-0016) |
| R-0014 | 2026-10-19 | 4 | R-0012 as CTranslate2 int8 (laptop CPU), sw tag | (same as R-0012) | Soapies engxho test, 391 clips | **79.59** | **38.43** | 0 | 0 | stage 4 starting point; English words right 32 %, isiXhosa 15 %; spells English the isiXhosa way. Stock medium run stopped (P-0013) |
| R-0017 | 2026-10-19 | 5 | R-0007 as ONNX int8 for the browser (transformers.js), laptop CPU | (same as R-0007) | NCHLT xho test, 200 unseen-sentence clips | 37.71 | 6.63 | 0 | 0 | same clips on GPU fp16: 36.35 / 6.43; 163/200 identical; powers the free in-browser demo (D-0020) |
| R-0018 | 2026-10-21 | 3 | R-0012 model (no training) | (same as R-0012) | Swivuriso xho dev_test, 2145 clips 1-30 s without [?], 24 spk, 9.4 h | 37.32 | 9.00 | - | - | the "before" for R-0019; read 33.4 / 7.6, **unscripted 42.4 / 10.8**; ran on the R-0019 node |
| R-0019 | 2026-10-21 | 3 | whisper-medium fine-tuned, 4000 steps, sw tag | R-0012's data + Swivuriso train 146.6 h (32 397 clips, 407 spk; 6 139 clips dropped as test/dev sentences) = 210.8 h | Swivuriso xho dev_test, 2145 clips | **19.12** | **4.12** | 2.97 | 5.53 | one change vs R-0012 (+Swivuriso); read 19.2 / 4.1, **unscripted 19.0 / 4.1** (R-0018: 42.4 / 10.8); L40S, batch 8 x 4, 34.6 GB peak, best = step 4000 (dev CER 2.91, still falling) |
| R-0019 | 2026-10-21 | 3 | (same model) | (same) | FLEURS xh test, 1034 clips | **30.32** | **6.24** | - | - | R-0012: 37.83 / 8.03 (22 % fewer letter errors) |
| R-0019 | 2026-10-21 | 3 | (same model) | (same) | NCHLT xho test, 2770 clips | 13.67 | 2.31 | - | - | R-0012: 12.71 / 2.33; seen sentences 10.7 / 1.8 (R-0012 9.0 / 1.7), **unseen 26.6 / 4.4 (R-0012 28.7 / 5.0)** |
| R-0020 | 2026-10-21 | 3 | R-0019 as CTranslate2 int8 (laptop CPU) | (same as R-0019) | NCHLT xho test, 200 unseen-sentence clips | 28.16 | 5.01 | 0 | 0 | same clips on GPU fp16: 27.65 / 4.95; 184/200 identical; 742 MB, ~7 s per clip; R-0013 (R-0012-int8) on the same clips: 31.74 / 5.67 |
| R-0021 | 2026-10-21 | 3 | R-0019-int8 (laptop CPU), **beam search 5** instead of greedy | (same as R-0019) | NCHLT xho test, 200 unseen-sentence clips | 27.65 | 4.73 | 0 | 0 | greedy on the same clips (R-0020): 28.16 / 5.01; 14 clips better, 9 worse; no slowdown (6.84 s per clip) |
