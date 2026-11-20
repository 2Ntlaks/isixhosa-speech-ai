# Lead verification: Neon's browser-medium report (2026-11-20)

Report checked: `docs/research/neon-browser-medium-2026-11-20.md` (Neon, Gemini 4 Neon, thought level xhigh).
Neon changed no other file and spent $0 (git status: only its report was new).

## How it was checked
- **Repo facts, all checked against the files:** R-0035 and R-0027 scores, R-0028 ONNX sizes and +0.16 CER, R-0027's
  old recipe on the same 309.7 h, R-0036/R-0037 int8 numbers, laptop onnxruntime 1.27.0. All correct.
- **Hugging Face file sizes, checked with the Hub API:** onnx-community/whisper-medium-ONNX q4f16 180.63 + 336.28 MB,
  q4 209.95 + 469.35 MB, fp16 encoder 614.72 MB; silero-vad q8 0.64 MB; our small ONNX 98.19 + 196.58 MB. All exact.
- **transformers.js 4.3.2 code, read directly (raw file of the 4.3.2 tag):** `// NOTE: For now, we don't support spawning
  new beams` (L957) and `// TODO: Support beam search` (L1017) are there: no beam search. `decoder_forward` (L1355 on)
  never sets `cache_position`, so P-0015's export pin is still needed. npm: 4.3.2 depends on
  onnxruntime-web 1.31.0-dev.20260914-8d85527a0 (exact).
- **Sources read by a fetch agent:** dtypes.md encoder-sensitivity warning (true); webgpu.md "As of March 2026, global
  WebGPU support is around 85%" (true, eight months old); realtime-whisper-webgpu worker uses encoder fp32 and decoder
  q4 with "'fp16' is broken" (true; main branch); whisper.cpp v1.9.5 whisper.wasm README "up to size small inclusive...
  unsatisfactory" (true); Ferraz et al. 2311.01070 Tables 1-2 (numbers true); Distil-Whisper 2311.00430 Tables 11-12
  (numbers true, read from a summary of the page); uDistil-Whisper 2407.01257 Swahili Table 12 (true, from a summary);
  Söhler et al. 2511.08093 whisper-small test-other numbers (true, verbatim).

## Corrections
1. **Safari 7-day rule: right rule, wrong source and slightly wrong trigger.** WebKit blog 14403 (cited) does not state
   7 days. The rule is on https://webkit.org/tracking-prevention/ ("ITP deletes all cookies created in JavaScript and
   all other script-writeable storage after 7 days of no user interaction with the website"). The page also exempts
   web apps added to the home screen. Neon's "7 days of browser use" wording is not what that page says.
2. **Ferraz et al. Table 2** compares CLSR fine-tuning against CLSR + distillation, not plain fine-tuning against
   distillation. The 0.2-0.6 WER gain stands; the label was wrong.
3. **The ~85% WebGPU figure is from March 2026**, not today.
4. Speed, memory and cost figures for the browser and for new training runs are Neon's estimates, clearly marked as
   inference in the report. None is measured yet.

## Verdict on research quality
High. No invented source found; every sampled number matched its source, and the most decision-relevant claims (no
beam search, the cache_position bug still open, file sizes, encoder sensitivity, whisper.cpp's own "small at most")
were confirmed at the code or file level. Two citation slips (above), both minor and neither changes the
recommendation. Facts and inferences are separated well, and the test plan sets its pass/fail bars before running.

## Lead's view of the recommendation
Agree with the order: (1) a $0 laptop test of R-0035 as 4-bit ONNX (accuracy in Python, then speed and memory in
Chrome/Edge WebGPU), with Neon's bars; (2) if it passes, a hybrid demo: small by default, medium as an opt-in on
capable computers; (3) separately, retraining small with the R-0035 recipe (~$5, a founder decision) is the cheapest
way to improve the demo for phones. Distillation into small is not worth it now.
