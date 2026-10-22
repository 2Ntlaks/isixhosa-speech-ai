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
