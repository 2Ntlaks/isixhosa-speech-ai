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

## Browser check · 2026-10-22 ~08:00 SAST (laptop, $0)
- Headless Chrome, the demo's own `worker.js` (transformers.js 3.0.2, checksum-verified from npm) pointed at the local
  files instead of Hugging Face, served with COOP/COEP headers: `crossOriginIsolated` true, 16 threads.
- Model load 5.9 s from disk. NCHLT clip nchlt_xho_500m_0267 (3 s): "ingekazi" in 6.9 s, the same as the Python ONNX run
  above. Founder's recording 20261021-140009 (14.2 s): 9.4 s, WER 12.5 / CER 6.4 against his transcript
  ("kuthwita" for kutwitter, "theatre" for Thetha). R-0007-int8 (demo today, greedy) on the same recording: WER 37.5 /
  CER 7.3 ("leemodelethe tha", "ibeluncedo"). One recording: an illustration, not a score.
- CTranslate2 int8 copy for the laptop page and the model repo's ct2-int8/ (`data/models/R-0027-int8`, 240 MB): same
  200 clips CER 5.95 / WER 35.32 vs GPU 5.91 / 35.49, 188/200 identical, 2.44 s per clip.
