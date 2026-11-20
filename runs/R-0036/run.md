# R-0036 · R-0035 int8 copy on the laptop CPU (ship check, as R-0020)

Before the run (lead, 2026-11-20). Founder said yes to: check int8, private second copy, publish.

- **Why:** R-0035's ship rule: before it becomes Thetha's default, its int8 copy (what the live page runs) must score
  at most 0.3 CER above the GPU float16 copy on the same clips.
- **Model:** S3 models/R-0035-int8/ (CTranslate2 int8 with tokenizer.json, P-0020), copied to data/models/R-0035-int8.
- **Clips:** a seeded random 100 clips (seed 1) of NCHLT test and 100 of FLEURS test (public sets only; no Swivuriso
  or Soapies audio on the laptop). Decoding: R-0033 standard (beam 5 + loop guard), CPU int8, 8 threads.
- **Compare:** the same clip ids in runs/R-0035/gpu_fp16_beam5/eval_{nchlt,fleurs}/predictions.jsonl.
- **Pass:** CPU int8 CER <= GPU fp16 CER + 0.3 on each set's 100 clips.
- **Cost:** $0 compute; S3 download ~2 GB (model + public test audio).

## Command
```
CT2_USE_MKL=0 python src/eval_guarded.py --model data/models/R-0035-int8 --device cpu --compute-type int8 --threads 8 \
  --sample 100 --xml data/nchlt_xho/transcriptions/nchlt_xho.tst.xml --root data --out runs/R-0036/eval_nchlt
CT2_USE_MKL=0 python src/eval_guarded.py --model data/models/R-0035-int8 --device cpu --compute-type int8 --threads 8 \
  --sample 100 --fleurs-tsv data/fleurs_xh_za/test.tsv --fleurs-audio data/fleurs_xh_za/audio/test --out runs/R-0036/eval_fleurs
```
