# R-0013 · Does the fast CPU engine lose accuracy? (R-0012 as CTranslate2 int8, on the laptop)

- **Why:** the founder wants the live page (src/live.py, D-0014) faster on the laptop's CPU. R-0012 was converted to
  CTranslate2 with 8-bit weights (`ct2-transformers-converter --quantization int8`, 775 MB instead of 3.06 GB). Before
  the live page uses it, measure whether 8-bit costs accuracy.
- **What:** 200 NCHLT test clips whose sentence never occurs in training (seeded sample, seed 1), scored with the int8
  copy on the laptop CPU, compared clip by clip with R-0012's own GPU evaluation (fp16) on the same clips.
  Same prompt (<|sw|>, transcribe), greedy decoding, token limit 96, normalisation v1.
- **Command:** `CT2_USE_MKL=0 .venv/Scripts/python src/eval_ct2.py --model data/models/R-0012-int8 --reference runs/R-0012/eval_nchlt/predictions.jsonl --sample unseen:200 --out runs/R-0013`
- **Machine:** founder's laptop (AMD Ryzen 7 PRO 250, 8 cores, no usable GPU), $0. CT2_USE_MKL=0: Intel's MKL is
  slower on this AMD CPU (5.1 vs 5.8 s encoder time in a quick benchmark).
- **Earlier checks (20 listening clips):** int8 CER 3.16 = GPU 3.16, 19/20 outputs identical, ~6.2 s per clip
  (bfloat16 PyTorch ~7-8 s, fp32 ~11 s). Shortening the 30 s encoder window to the audio length (the whisper.cpp
  "audio_ctx" trick) broke the model: it repeats words (CER 488 % with 3 s margin), so it is not used.
- **Pass mark:** int8 CER within 0.3 points of the GPU CER on the same clips.

## Outcome · 2026-10-17 · PASSED (laptop, $0)
- 200 unseen-sentence NCHLT test clips. **int8 CPU: CER 5.67 %, WER 31.74 %. GPU fp16 (R-0012's own evaluation, same
  clips): CER 5.69 %, WER 31.06 %.** 186 of 200 outputs identical; in the 14 that differ, each engine is sometimes the
  closer one (e.g. int8 right on "thenji", "amanzi aya qina"; GPU right on "zemihla ngemihla"). Pass mark met.
- Speed: 6.97 s per clip on 8 CPU threads (CT2_USE_MKL=0), slowed by other work on the laptop during the run; ~6.2 s
  alone. Encoder ~5 s of that: Whisper always encodes a 30 s window, which is the fixed CPU cost.
- Size: 775 MB on disk (vs 3.06 GB), ~0.8 GB in memory (bfloat16 PyTorch: 1.9 GB).
- Decision: the live page (src/live.py) uses the int8 copies: R-0012-int8 (default) and R-0007-int8 (small, 248 MB).
