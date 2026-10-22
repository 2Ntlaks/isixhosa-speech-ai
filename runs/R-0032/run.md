# R-0032 · Thetha inside the Siyamthanda translator (a copy), against its current isiXhosa recognizer

- **Why:** the founder's "real real test": put Thetha into a real project as a drop-in engine. Siyamthanda (a
  friend's offline speech translator: microphone -> recognizer -> NLLB -> Piper English speech) currently recognizes
  isiXhosa with Meta's Omnilingual CTC 1B (int8 ONNX). The friend's project is never modified: everything runs in a copy
  (`C:\Users\ntlak\Downloads\siyamthanda-thetha-test`: translator/, bench/, the NLLB/Piper models and the isiXhosa test
  set copied; nothing of it goes into this repo).
- **Engine:** `integrations/siyamthanda/thetha_engine.py` (same interface as their MetaTranslator; faster-whisper,
  int8, language sw, task transcribe, greedy; their sentence restoration and NLLB 600M unchanged).
  `integrations/siyamthanda/bench_thetha.py` runs their own `bench/bench_e2e.py` with the engine swapped in.
- **Test set:** their frozen `datasets/zu_xh_test100`, isiXhosa part: 100 FLEURS **test** clips (2-29 s; seed 2029).
  Thetha never trained on FLEURS test (FLEURS train only; test/dev sentences excluded from Swivuriso), so it is a
  held-out test for all models. Their scoring: recognizer WER/CER (their normalisation), translation BLEU/chrF2 vs
  FLEURS English, processing time from end of speech to first English audio.
- **Compared:** Thetha R-0029 (new medium), R-0019 (current medium), R-0027 (small); Meta 1B re-run in the same session
  (their recorded run, 2026-10-06, same laptop on battery: WER 35.97, CER 6.52, BLEU 18.19, first audio median 5.97 s).
- **Command:** `bash runs/R-0032/run.sh` (laptop, $0; one recognizer at a time, laptop memory is short).
- **Smoke test (3 clips, R-0029):** works; recognizer ~10 s per 12 s clip on battery vs Meta ~4 s: Whisper always
  encodes a full 30 s window, CTC only the audio. Speed may decide the live use; hence the small model too.
- **Attempt 1 (14:35 SAST) stopped:** Claude Code stopped the run because the laptop was critically low on memory
  (14.6 GB total, ~1 GB free with the founder's other apps open; the R-0029 benchmark process held 1.4 GB). The
  leftover Python process was stopped by hand; no results were written. Waiting for the founder to free memory or
  choose to run it elsewhere.
- **Founder's choice (14:45 SAST): B**, run it in the cloud: a copy of the Siyamthanda code (translator/, bench/,
  requirements-meta.txt), its NLLB/Piper models and the isiXhosa test set go to the private S3 path
  private/siyamthanda-copy/ (not this repo, not public). Node: c7i.4xlarge spot (16 vCPU, close to the laptop's 8-core
  Ryzen 7), ~$0.30-0.40/h, about 1 h. Speeds are the node's, not the laptop's; accuracy is the same either way.
  `FALLBACK_TYPES="c6i.4xlarge c7i.8xlarge" cloud/run_job.sh --run R-0032 --type c7i.4xlarge --market spot --max-hours 2`

## Outcome (2026-10-22, 17:20 SAST): Thetha hears isiXhosa better; the English barely changes (NLLB is the limit)

- **Node:** c7i.8xlarge spot (Xeon 8488C; the 4xlarge had no capacity), 17:01-17:21 SAST, **~$0.25**. Packages: the
  project's pins (faster-whisper 1.2.1, ctranslate2 4.8.2, onnxruntime 1.30.0, transformers 4.57.3, sacrebleu 2.6.0,
  piper-tts 1.8.0). Same threads as the project (recognizer 8, NLLB 4), one recognizer at a time, warm-up excluded.
- **Check that the setup is faithful:** the Meta 1B re-run reproduces the project's recorded 2026-10-06 run exactly on
  recognition (WER 35.97, CER 6.52) and within noise on translation (BLEU 18.08 vs 18.19).

| Recognizer (100 isiXhosa FLEURS test clips) | WER % | CER % | BLEU | chrF2 | recognize (median s) | to first English audio (median / p95 s) |
|---|---|---|---|---|---|---|
| Meta Omnilingual CTC 1B int8 (project's current) | 35.97 | 6.52 | 18.08 | 46.35 | 1.37 | 2.08 / 3.61 |
| **Thetha R-0019 medium int8** | **30.36** | **5.91** | 18.76 | 47.30 | 1.96 | 2.66 / 3.68 |
| Thetha R-0029 medium int8 | 30.80 | 5.95 | 18.09 | 47.06 | 1.95 | 2.67 / 3.76 |
| Thetha R-0027 small int8 | 37.91 | 11.03 | 17.07 | 44.88 | 0.95 | 1.64 / 2.38 |

- **Recognition (paired, same clips):** Thetha medium makes clearly fewer word errors than Meta: R-0019 -5.6 points
  (95 % CI -8.2 to -3.1; better on 60 clips, worse on 17), R-0029 -5.2 (CI -7.7 to -2.5; 59 / 26). Thetha small is no
  better than Meta (+1.9, CI -0.6 to +4.5) and has 1.7x its letter errors.
- **Translation (the project's paired bootstrap, bench/compare_af_systems.py, 1,000 samples, Meta = baseline):** no
  significant change: R-0019 BLEU +0.7 (p 0.19), chrF2 +1.0 (p 0.07); R-0029 BLEU +0.0 (p 0.42), chrF2 +0.7 (p 0.13);
  R-0027 BLEU -1.0 (p 0.14), chrF2 -1.5 (p 0.03, worse). BLEU's 95 % half-width is ~2.6-3.0.
- **Why better ears do not show in the English:** NLLB 600M is the bottleneck. The project's own dev check
  (docs/zulu-xhosa-meta-path-2026-10-06.md) shows that even the *correct* isiXhosa text, written the way a recognizer
  writes it, only reaches BLEU ~19-21; Meta's output already gets 17.5-18. There is little room left for the recognizer
  to win on read news sentences.
- **Speed (cloud CPU, not the laptop):** Thetha medium adds ~0.6 s before the first English word (2.66 vs 2.08 s
  median; p95 about equal). The small model is fastest (1.64 s) but hears worse, so it is not useful here.
- **R-0029 vs R-0019:** a tie on this read-speech set (R-0019 marginally ahead); R-0029's gains were on unscripted
  and mixed speech (R-0029, R-0031), which this set does not contain.
- **What it means for Siyamthanda:** swapping in Thetha medium gives ~15 % fewer isiXhosa word errors for +0.6 s, but
  the English the listener hears will not be measurably better until the translation step improves (e.g. NLLB 1.3B,
  which the project already supports, or better sentence restoration). A test on conversational isiXhosa, where Meta is
  likely weaker, is where Thetha's advantage should be largest. Whether to offer it to the friend is the founder's call.
- Files: the four per-clip CSVs and summaries (FLEURS text, CC BY 4.0), compare.json. The Piper English WAVs stay out
  of git. The private copy of the friend's code stays in S3 private/siyamthanda-copy/ until the founder says to delete it.
