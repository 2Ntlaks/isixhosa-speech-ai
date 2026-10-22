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
