# R-0026 · Make Thetha faster on the laptop CPU without changing its answers (R-0019-int8, $0)

- **Why:** the founder wanted inference optimised for speed. PR #2 (R-0025) bounded memory (-17 % on a 48 s recording)
  but did not make anything faster (+5.5 % time on 48 s). This run looks for real speed.
- **Machine:** founder's laptop (Ryzen 7 PRO 250, 8 cores / 16 threads), CTranslate2 4.5.0 int8, CT2_USE_MKL=0,
  nothing else running. Script: `runs/R-0026/speed.py` (modes split, threads, context, validate).

## Part 1 · where the time goes (32 seed-22 NCHLT test clips, mean 4.2 s of audio), 21 Oct ~22:30 SAST
| Step | seconds per clip |
|---|---|
| audio -> features | 0.006 |
| **encoder ("listening")** | **2.89** |
| decoder, beam 5 | 1.01 (greedy 0.89) |
| total (generate) | 3.86 |
- Three quarters of the time is the encoder. Whisper always encodes a 30 s window, even for 4 s of speech.
- **Threads** (encoder, 8 clips): 4 = 3.12 s, 6 = 3.05, 8 = 3.09, 12 = 3.45, 16 = 3.42. No gain from more threads; keep 8.
- **Shorter encoder window, no other change** (`context.json`): audio + 2 s: 1.25 s per clip but WER 88 / CER 67
  (14/32 identical); audio + 1 s: WER 171. The model was trained only on 30 s windows and runs on (repeats) when the
  window is short.
- **Quick probe (32 clips, exploratory, not a result):** window max(10 s, audio + 1 s) plus an output cap of
  8 tokens per second + 8, repetition_penalty 1.1 and no_repeat_ngram_size 4: **WER 21.74 / CER 3.47 at 1.49 s per clip**
  vs 21.74 / 3.59 at ~4.0 s with the full window; 25/32 identical. 15 s window: 20.65 / 3.47, 1.92 s; 20 s: 21.74 / 3.72, 2.27 s.

## Part 2 · validation (planned before running)
- **Clips:** 200 NCHLT test clips (R-0021's sample, includes the 32 above) + 100 NCHLT dev clips (R-0022). Three settings
  on every clip, order alternating: **now** (30 s window, beam 5, limit 225 = live page), **guards** (cap +
  repetition settings only), **fast** (guards + window max(10 s, audio + 1 s)).
- **Command:** `CT2_USE_MKL=0 .venv/Scripts/python runs/R-0026/speed.py validate`
- **Pass rule for "fast":** on each set, WER and CER at most 0.3 points worse than "now", and at least 2x faster.
  "guards" shows whether the repetition settings alone change answers.
- Not covered: long recordings (> 30 s, several windows) and the founder's own speech; check before switching the page.
