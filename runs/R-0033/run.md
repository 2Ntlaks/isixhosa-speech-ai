# R-0033 · R-0019 re-scored with a loop guard (Whisper's reliability rules), GPU and CPU

Before the run (drafted by the builder 2026-11-19; the lead fills in the outcome). Plan: D-0031, step 1.

- **Why:** every score so far came from plain greedy decoding with no protection against runaways (the model getting
  stuck repeating itself). One runaway (a 23.6 s clip written as 901 letters) cost R-0029 its ship rule by 0.02 CER.
  Whisper's own paper decodes with a guard: if the text compresses too well (a loop), decode that clip again by
  sampling. This run measures R-0019, the published medium model, with that guard, so that R-0035 and later models
  are compared under the same, safer decoding. R-0029 can no longer be re-scored (its weights are lost, P-0021).
- **Model:** `Ntlakanipho/whisper-medium-isixhosa` at revision `603a39b5f70526ef2192e5d6f80f713c682a1d39` (Hugging
  Face main = R-0019). GPU: the full weights converted to CTranslate2 float16 on the node (`src/make_ct2.py`). CPU: the
  published `ct2-int8/` copy (what the live page and the Siyamthanda test run), plus a tokenizer.json built from its own
  tokenizer files.
- **Evaluator:** `src/eval_guarded.py` (faster-whisper 1.2.1, ctranslate2 4.5.0, `WhisperModel.transcribe`, never the
  batched pipeline, which ignores the fallback temperatures). Settings (Neon's pre-flight memo, checked by the lead):
  language sw, task transcribe, no timestamps, no previous text, no VAD (test clips are already cut);
  compression-ratio threshold 2.4; fallback temperatures 0.0, 0.2, 0.4, 0.6 with best of 5; log-probability and
  no-speech checks OFF (the first would resample hard but correct clips at random, the second relies on a
  `<|nospeech|>` token our fine-tunes never trained on); no repetition penalty (R-0026: it hurt); token limits as in
  every earlier evaluation (NCHLT 96, FLEURS 225, Swivuriso 440, Soapies 96). Sampling is seeded per clip.
- **Two arms on the same clips:** beam 1 (greedy + guard) and beam 5 (beam search + guard), CTranslate2 float16 on
  the GPU. Beam 1 vs the October greedy numbers shows what the guard alone changes; beam 5 vs beam 1 what the beam adds.
- **Test sets (exactly the earlier clip lists, `src/testsets.py`, `src/scoring.py` normalisation v1):** NCHLT test
  2770 clips (seen 2259 / unseen 511), FLEURS test 1034 clips <= 30 s, Swivuriso dev_test 2145 clips (1-30 s, no [?];
  scripted 1422 / unscripted 723), Soapies test 391 clips. FLEURS comes back from Hugging Face google/fleurs at revision
  `70bb2e84b976b7e960aa89f1c648e09c59f894dd` (its S3 copy is gone, P-0021); checked on the laptop: it gives exactly
  R-0019's 1034 test clips and texts, and the test archive's SHA-256 matches the published one.
- **Also recorded per clip and per set:** whether a fallback fired, at which temperature the kept text came from,
  the first and kept compression ratio, clips that exhausted every temperature, empty outputs; CER without spaces;
  runaway count (> 2.5x the reference and > 150 letters); FLEURS references with and without digits; seconds per clip
  (after one untimed warm-up decode, as for Meta's models).
- **Reproduction check first:** the October evaluator (`src/baseline.py`, transformers greedy fp16) on NCHLT, FLEURS and
  Swivuriso with the same Hugging Face weights. It must give R-0019's recorded scores again (same clip counts, CER
  within 0.05, WER within 0.2): NCHLT 13.67 / 2.31, FLEURS 30.32 / 6.24, Swivuriso 19.12 / 4.12 (WER / CER). This proves
  that the re-fetched data and the published weights are what R-0019 was scored on. October ran on an L40S, this node
  has an L4 (same Ada generation); tiny fp16 differences are possible, hence the small tolerance.
- **CPU part (timed, nothing else running):** the int8 copy, beam 5 + guard, 8 threads, on 50 seeded clips per test
  set (the same 200 clips R-0034 times Meta's models on).
- **Same node, in this order (Neon's code review F-03):** reproduction check (Meta's venv and weights download in the
  background meanwhile, CPU and network only) -> R-0033 on the GPU in 3 lanes (~3 GB each, well under the L4's 22 GB;
  memory logged every minute, peak reported) -> R-0034 alone on the GPU -> R-0033 CPU timing -> R-0034 CPU timing.
  R-0034 runs in a clean environment (no job-venv library path, F-02) and its failures are recorded
  (`out/R-0034/FAILED`), never stopping R-0033.

## Rules set before the run
1. **Reproduction check** fails (any set outside the tolerance) -> the job stops there (exit 1, before the GPU
   lanes) and nothing from this run is interpreted; the lead finds out why first (data or weights differ).
2. **The standard decoding from now on** is beam 5 + loop guard, CTranslate2 float16 on the GPU, with the settings
   above. R-0019's beam-5 guarded scores from this run are the numbers R-0035 must beat (its ship rule names them).
3. **int8 check (as R-0020 / R-0031):** pooled over all 200 timed clips (the four 50-clip sets together, one CER),
   the int8 CPU copy's CER is at most 0.3 above the GPU float16 beam-5 CER on the same 200 clips. The per-set numbers
   are reported but do not decide (50 clips per set are too few).
4. No ship rule: R-0019 stays the published model whatever these numbers say; this run only changes how we measure.

- **Expected, not a rule:** the guard fires on very few clips (< 1 %); beam 5 a little better than greedy (R-0021: CER
  5.01 -> 4.73 on 200 NCHLT unseen clips); no runaways left in the beam-5 arm.

## Command
```
DISK_GB=150 FALLBACK_TYPES="g6.4xlarge g6e.xlarge" cloud/run_job.sh --run R-0033 --type g6.2xlarge --market ondemand --max-hours 4
cloud/wait.sh R-0033 && cloud/collect.sh R-0033 && mv runs/R-0033/R-0034/* runs/R-0034/ && rmdir runs/R-0033/R-0034
```
- **Machine:** g6.2xlarge on-demand (NVIDIA L4 24 GB, 8 vCPU, 32 GB RAM), us-east-1, $0.978/h. Fallbacks are
  on-demand only: g6.4xlarge (16 vCPU; the on-demand G quota is now 32 vCPU, checked by the lead; the spot quota is 8,
  so never with `--market spot`), then g6e.xlarge. Root disk 150 GB (F-05): the AMI and the job venv take ~55 GB,
  Meta's venv ~10 GB, models ~15 GB, test audio ~3 GB.
- **Time and cost estimate (R-0033 and R-0034 together, after Neon's review):** boot and installs ~10 min; data
  and R-0019 download and conversion ~10 min; preflight ~2 min; reproduction check ~20-22 min (L40S took 7.2 min in
  October; the L4 has about a third of its memory bandwidth); R-0033 GPU lanes ~40-55 min (3 lanes; the longest is
  Swivuriso beam 5, 2145 clips one at a time; faster-whisper's GPU speed on this model was never measured here, so
  this is the least certain number); R-0034 GPU alone ~15 min; R-0033 CPU timing ~25-30 min (200 clips); R-0034 CPU
  timing ~15-20 min (float32 for both models, 200 clips each, plus a 20-clip bfloat16 probe of 300M; stopped by a
  45 min budget whatever happens). **About 2.3-3 h, about $2.30-2.90; cap 4 h ($3.91 at most).**
- **Laptop checks before launch (builder, 2026-11-19):** 34 unit tests pass; the evaluator scored 60 real FLEURS test
  clips with the published small model (R-0027 int8, laptop CPU): CER 6.99 vs R-0027's recorded greedy 7.65 on the
  same clips (same references); on the two clips R-0027 looped on, greedy looped again (ratio 2.63, CER 132.0) and the
  guard kept the 0.4 sample (ratio 1.32, CER 24.0); beam 5 alone already avoided both loops. The whole job was
  rehearsed with whisper-tiny on synthetic data (stand-ins for AWS and the GPU), before and after Neon's code review
  fixes (see the builder's report), including a failing reproduction check and a failing R-0034.
- Swivuriso and Soapies per-clip outputs and samples stay out of git (.gitignore: `runs/**/eval_swivuriso*/`,
  `runs/**/eval_soapies*/` predictions and samples).
