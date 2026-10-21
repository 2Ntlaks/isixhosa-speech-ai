# R-0020 · R-0019 as CTranslate2 int8 for the laptop (does 8-bit lose accuracy?)

- **Why:** R-0019 is the best model (stage 3 more data). The live page (src/live.py) runs 8-bit CTranslate2 copies on
  the laptop CPU; R-0013 showed 8-bit cost nothing for R-0012. Same check for R-0019 before it replaces R-0012-int8.
- **What:** `ct2-transformers-converter --model data/models/R-0019 --output_dir data/models/R-0019-int8 --quantization int8`
  (tokenizer and preprocessor files copied, as R-0012-int8), then 200 NCHLT test clips whose sentence never occurs in
  training (seed 1, as R-0013), compared clip by clip with R-0019's own GPU evaluation.
- **Command:** `CT2_USE_MKL=0 .venv/Scripts/python src/eval_ct2.py --model data/models/R-0019-int8 --reference runs/R-0019/eval_nchlt/predictions.jsonl --sample unseen:200 --out runs/R-0020`
- **Machine:** founder's laptop, $0. Only this heavy job on the laptop while it runs (P-0013).
- **Pass mark:** int8 CER within 0.3 points of the GPU CER on the same clips.
