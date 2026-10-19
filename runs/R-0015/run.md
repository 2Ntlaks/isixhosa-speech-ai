# R-0015 · Stage 4: does adding South African English teach R-0012 to write English words in English?

- **Why:** R-0014 showed R-0012 spells English words inside isiXhosa speech the isiXhosa way ("e stubborn" ->
  "istabhunga", "party" -> "pathi"): it has only ever seen isiXhosa text. Stage 4 recipe, decided in D-0017.
- **What:** continue training R-0012 (not stock medium) for 2000 steps, lr 5e-6 (half of R-0012's, to keep what it
  knows), warmup 200, batch 8 x 4. Data: R-0012's own (NCHLT isiXhosa train + FLEURS train, <|sw|>) **plus 10 h of
  NCHLT English** (South African speakers, short phrases, learned with Whisper's own <|en|> tag).
- **Best checkpoint:** lowest CER on the Soapies dev set (536 clips, 38 speakers; none of the 5 test speakers; never
  trained on, D-0016). NCHLT dev and FLEURS dev scored for information.
- **Scored on:** Soapies test (laptop, int8, same engine as R-0014; the stage 4 headline), NCHLT test and FLEURS test
  (GPU, same as R-0012; check that isiXhosa did not get worse).
- **Runs on the same node as R-0016** (runs/R-0015/job.sh): R-0016 = R-0015 + 8000 stitched clips (one change).
- **Command:** `DISK_GB=200 FALLBACK_TYPES="" cloud/run_job.sh --run R-0015 --type g6e.xlarge --market ondemand --max-hours 5`
- **Cost estimate:** ~2.5-3 h of L40S on-demand for both runs, about $5-6 together.
- **When:** after 1 November (October's mgaguli-gpu-monthly brake is at ~$17 of $20), unless the founder raises it.
- **Pipeline check before launch:** CPU smoke test on the laptop (whisper-tiny, 4 steps, local clips): see below.

## Pipeline check · 2026-10-19 · NOT FINISHED
- Verified on the laptop: labels for isiXhosa clips are identical to the old code (300/300 NCHLT clips); English clips
  get <|en|>; stitched clips join correctly (audio length = parts + silences, transcript in the same order); Soapies
  dev loads (536 clips, 32 kHz resampled). Data build in the smoke test: 2206 clips incl. 83 English + 40 stitched.
- The 4-step training smoke test was stopped by low laptop memory before its first step (P-0013). Must pass before
  launch: re-run alone with `--dev-clips 8` and a short Soapies dev (or on the GPU node as a 20-step preflight).
