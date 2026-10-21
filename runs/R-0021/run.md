# R-0021 · Beam search instead of greedy decoding (laptop, R-0019-int8)

- **Why:** the founder asked how to cut word errors now, without retraining. Every evaluation so far used greedy
  decoding (one best token at a time). Beam search keeps the 5 best partial transcripts and picks the best whole one,
  which often fixes 1-2 letter slips inside long words. It costs extra decoder time on the CPU.
- **One change vs R-0020:** `--beam-size 5`. Same model (R-0019-int8), same 200 unseen-sentence NCHLT test clips
  (seed 1), same token limit (96), same normalisation.
- **Command:** `CT2_USE_MKL=0 .venv/Scripts/python src/eval_ct2.py --model data/models/R-0019-int8 --reference runs/R-0019/eval_nchlt/predictions.jsonl --sample unseen:200 --beam-size 5 --out runs/R-0021`
- **Machine:** founder's laptop, $0.
- **Pass mark:** CER at least 0.2 points below R-0020's 5.01 with seconds per clip no more than 1.5x greedy (7.16 s).
  If it passes, test FLEURS-style long sentences next before switching the live page.
