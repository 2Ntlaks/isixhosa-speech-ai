# R-0028 · Does the in-browser copy of R-0027 (ONNX, 8-bit) keep its accuracy?

- **Why:** the free demo runs the model inside the visitor's browser (transformers.js 3.0.2). Same check as R-0017 did
  for R-0007, before publishing anything.
- **What:** `src/export_onnx.py` (R-0017's recipe, now saved as code: optimum 1.20.0 / transformers 4.41.2 in
  .venv-onnx2, untied output layer, QUInt8 dynamic quantisation of MatMul + Gather incl. subgraphs). Files:
  encoder_model_quantized.onnx 98.2 MB, decoder_model_merged_quantized.onnx 196.6 MB (R-0007's: 98.2 / 196.6 MB).
  Decoder inputs identical to the published R-0007 files (no `cache_position`, P-0015).
- **Command:** `.venv-onnx/Scripts/python src/eval_onnx.py --model data/onnx/R-0027 --reference runs/R-0027/eval_nchlt/predictions.jsonl --sample unseen:200 --out runs/R-0028`
- **Pass mark:** CER within 0.3 points of R-0027's own GPU CER on the same 200 unseen-sentence NCHLT test clips (seed 1).

## Outcome · 2026-10-22 · PASSED (laptop, $0)
- ONNX int8 **CER 6.07 / WER 35.49** vs GPU fp16 5.91 / 35.49 on the same clips (+0.16 CER); 175/200 outputs identical
  (R-0017: 163/200). 2.99 s per clip in Python on the laptop CPU.
- For comparison, R-0007's browser copy on its own 200 clips scored 6.63 / 37.71 (R-0017).
- Browser check: see below.
