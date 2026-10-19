# R-0017 · Does the in-browser copy of R-0007 (ONNX, 8-bit) keep its accuracy?

- **Why:** the free online demo runs the model inside the visitor's browser (D-0020, transformers.js). That needs an
  ONNX copy with 8-bit weights. Measure it before publishing, as R-0013 did for the laptop copy.
- **What:** R-0007 exported with optimum 1.23.3 (`optimum-cli export onnx --task automatic-speech-recognition-with-past`),
  then encoder_model and decoder_model_merged quantised with onnxruntime 1.31 `quantize_dynamic` (QUInt8, MatMul +
  Gather, EnableSubgraph for the merged decoder): 98 MB + 195 MB. Scored with onnxruntime on the laptop CPU on the same
  200 unseen-sentence NCHLT test clips as R-0013 (seed 1), compared clip by clip with R-0007's own GPU evaluation.
  Same prompt (<|sw|>, transcribe), greedy decoding, token limit 96, normalisation v1.
- **Command:** `.venv-onnx/Scripts/python src/eval_onnx.py --model data/onnx/R-0007 --reference runs/R-0007/eval_nchlt/predictions.jsonl --sample unseen:200 --out runs/R-0017`
- **Pass mark:** CER within 0.3 points of the GPU CER on the same clips.
- **Machine:** laptop, $0. The browser itself is checked separately (same ONNX files, transformers.js).

## Outcome · 2026-10-19 · PASSED (laptop, $0), after two export fixes
- Attempt 1 (optimum 1.23.3 / transformers 4.46.3): accuracy passed (ONNX int8 CER 6.65 / WER 37.20 vs GPU 6.43 /
  36.35; 167/200 identical), but in the browser transformers.js 3.0.2 failed: `Missing the following inputs:
  cache_position` (P-0015). optimum 1.21.3 / transformers 4.43.4 exported the same input.
- Attempt 2 (optimum 1.20.0 / transformers 4.41.2, before Whisper had cache_position): browser-compatible, but the
  decoder was 316 MB: the tied output layer kept a full-precision copy of the 159 MB word-embedding table (P-0015).
  Fixed by storing a pre-transposed copy so quantisation reaches it: decoder 197 MB, encoder 98 MB.
- **Final (scored on the exact files published): ONNX int8 CER 6.63 / WER 37.71 vs GPU fp16 6.43 / 36.35 on the same
  200 unseen-sentence clips; 163/200 outputs identical. Pass mark (0.3 CER points) met.**
- Browser check (headless Chrome 16 threads, transformers.js 3.0.2, live Space): the test clip transcribed exactly
  ("nangaphandle koko kungaqondani"); first visit 32 s including the ~300 MB download, then 7.3 s per clip with
  cross-origin isolation (multi-threaded) and 18.7 s without. Phone-sized layout checked by screenshot.
- Files: Ntlakanipho/whisper-small-isixhosa onnx/ (encoder_model_quantized.onnx, decoder_model_merged_quantized.onnx)
  and tokenizer.json; demo https://ntlakanipho-thetha.static.hf.space.
