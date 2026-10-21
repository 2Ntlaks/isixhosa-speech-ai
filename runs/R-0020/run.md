# R-0020 · R-0019 as CTranslate2 int8 for the laptop (does 8-bit lose accuracy?)

- **Why:** R-0019 is the best model (stage 3 more data). The live page (src/live.py) runs 8-bit CTranslate2 copies on
  the laptop CPU; R-0013 showed 8-bit cost nothing for R-0012. Same check for R-0019 before it replaces R-0012-int8.
- **What:** `ct2-transformers-converter --model data/models/R-0019 --output_dir data/models/R-0019-int8 --quantization int8`
  (tokenizer and preprocessor files copied, as R-0012-int8), then 200 NCHLT test clips whose sentence never occurs in
  training (seed 1, as R-0013), compared clip by clip with R-0019's own GPU evaluation.
- **Command:** `CT2_USE_MKL=0 .venv/Scripts/python src/eval_ct2.py --model data/models/R-0019-int8 --reference runs/R-0019/eval_nchlt/predictions.jsonl --sample unseen:200 --out runs/R-0020`
- **Machine:** founder's laptop, $0. Only this heavy job on the laptop while it runs (P-0013).
- **Pass mark:** int8 CER within 0.3 points of the GPU CER on the same clips.

## Outcome · 2026-10-21 · PASSED (laptop, $0)
- 200 unseen-sentence NCHLT test clips (same seed and clips as R-0013). **int8 CPU: CER 5.01 %, WER 28.16 %. GPU fp16
  (R-0019's own evaluation, same clips): CER 4.95 %, WER 27.65 %.** 184 of 200 outputs identical. Pass mark met.
- Same clips, previous laptop model (R-0013, R-0012-int8): CER 5.67 / WER 31.74.
- Speed 7.16 s per clip (8 threads, CT2_USE_MKL=0, other work on the laptop at the same time); size 742 MB.
- Decision for the live page: R-0019-int8 can replace R-0012-int8 as the default (founder to try it first).
