# R-0029 · whisper-medium + Swivuriso long-clip pieces (one change vs R-0019)

- **Why:** the founder wants the medium model improved before a real-world test inside the Siyamthanda translator (a
  drop-in engine, tested on a copy). R-0027 showed the long-clip pieces help the small model, but changed two things at
  once (short clips and pieces). This run measures the pieces alone, on the model that serves real projects.
- **One change vs R-0019:** + the 20,563 pieces (98.9 h, 83.7 h unscripted) cut from Swivuriso train clips over 30 s
  (src/swivuriso_long.py; R-0027's quality gate kept all; cached in S3 datasets/swivuriso_xho_long/). Everything else as
  R-0019: whisper-medium, 4000 steps, batch 32 (8 x 4, falls back to 4 x 8 if memory is short), lr 1e-5, warm-up 500,
  bf16, the same test/dev sentence exclusions, the same 6 NCHLT dev speakers.
- **Scored on:** NCHLT test, FLEURS test, Swivuriso test (same clips and settings as R-0019). The mixed isiXhosa-English
  test (Soapies, laptop) follows on the laptop with the int8 copy, against R-0019 and R-0027.
- **Pass / ship rule (set before the run):** better than R-0019 on Swivuriso test and FLEURS test (CER), NCHLT test CER
  not worse by more than 0.3. If it passes: int8 copy checked on the laptop, then Thetha's default and (with the
  founder's OK) the published medium model.
- **Command:** `DISK_GB=300 FALLBACK_TYPES="g6e.2xlarge" cloud/run_job.sh --run R-0029 --type g6e.xlarge --market ondemand --max-hours 6`
- **Cost estimate:** ~3.3 h x $1.861 (g6e.xlarge) = ~$6-7.5 (g6e.2xlarge $2.24/h if the xlarge has no capacity).
  October GPU spend before: ~$26 (D-0026 allows passing the $30 brake).

## Outcome (2026-10-22, 13:20 SAST): FAILED the ship rule by 0.02 CER on Swivuriso; one runaway output is the cause

- **Node:** g6e.2xlarge (L40S, xlarge had no capacity), 10:45-13:17 SAST, ~2.5 h x $2.24 = **~$5.70**. Training 7,119 s
  (1 h 59 min), batch 8 x 4, 34.65 GB peak, 309.7 h total data (Swivuriso 245.4 h, 52,960 clips, 407 speakers),
  best = step 4000 (NCHLT dev CER 2.99; R-0019 2.91). Model in S3 models/R-0029/ (2.8 GB).

| Test | R-0019 WER / CER | R-0029 WER / CER |
|---|---|---|
| Swivuriso test (2145 clips) | 19.12 / 4.12 | **18.12** / 4.14 |
| . read (1422) | 19.2 / 4.1 | 19.2 / 4.5 |
| . unscripted (723) | 19.0 / 4.1 | **16.7 / 3.6** |
| FLEURS test (1034) | 30.32 / 6.24 | **29.80 / 6.16** |
| NCHLT test (2770) | 13.67 / 2.31 | 14.17 / 2.32 |
| . unseen sentences (511) | 26.6 / 4.4 | **25.9 / 4.2** |

- **Rule (set before):** better than R-0019 on Swivuriso and FLEURS CER, NCHLT CER not worse by > 0.3. FLEURS passes,
  NCHLT passes (+0.01), **Swivuriso CER fails: 4.14 vs 4.12.** Recorded as failed.
- **Why it missed:** one read clip (speaker 1fc9720a, 23.6 s, 228 reference letters) came out as a 901-letter runaway
  (the model got stuck repeating), adding 770 letter errors on its own (that speaker: CER 5.6 -> 11.2 while WER moved
  28.0 -> 27.7). R-0019 has no runaway on this test. Without that one clip R-0029 is 3.90 vs R-0019's 4.12 on the
  same clips. Total letter errors: R-0019 13,388, R-0029 13,455. This is a post-hoc look, not a re-scoring: the rule
  stands as set.
- **What it means:** the long-clip pieces help unscripted speech (CER 4.1 -> 3.6, WER 19.0 -> 16.7), the speech real
  projects hear, and slightly help FLEURS and NCHLT unseen sentences; but they also brought one runaway. A live engine
  can guard against runaways (faster-whisper's compression-ratio check retries such outputs), which the GPU eval does
  not use. Next (laptop, $0): int8 copy, R-0020-style check, Soapies mixed test, then the founder decides whether
  R-0029 serves the Siyamthanda test alongside R-0019.
- Swivuriso predictions/samples are gitignored (transcripts stay off the public repo).
