# R-0038 · Can R-0035 (medium) run in the browser? 4-bit ONNX copies, laptop test ($0)

Before the run (lead, 2026-11-20). Founder said "yes" to Phase 1 of Neon's plan
(docs/research/neon-browser-medium-2026-11-20.md §7, verified in docs/research/lead-verification-browser-medium-2026-11-20.md).

- **Why:** the browser demo runs the small model (R-0027). Neon found medium could run in a desktop browser on WebGPU if
  it is compressed to 4 bits (~520 MB). Nobody has measured what 4-bit costs this model in accuracy. Answer that first,
  at $0, before touching the public demo.
- **Model:** data/models/R-0035 (= S3 models/R-0035, = Hugging Face main dc2acbb6).
- **Export:** optimum 1.20.0 + transformers 4.41.2 in an isolated venv (C:\Users\ntlak\venvs\onnx-med), task
  automatic-speech-recognition-with-past; the decoder must have no `cache_position` input (P-0015). Output outside the repo
  in C:\Users\ntlak\isixhosa-speech-ai-data\onnx\R-0035 (gitignored data, never committed).
- **Candidates** (transformers.js's own quantisation settings: MatMul 4-bit, block 32, symmetric, accuracy level 4;
  q4f16 = that, then float16 with float32 inputs/outputs):
  - A: encoder q4f16 + decoder q4f16 (expected ~520 MB), the one Neon recommends.
  - B: encoder fp16 + decoder q4f16 (~950 MB), only if A fails or for diagnosis.
  - C: q4 + q4 (~680 MB) and D: q8 + q8 (~830 MB), only if needed.
- **Decoding:** greedy (transformers.js has no beam search), prompt <|sw|> transcribe no timestamps, plus a loop guard
  in the browser's style: if the text's gzip compression ratio is > 2.4, retry with temperature 0.2, 0.4, 0.6 (seeded).
  Token limit 225 on FLEURS and 96 on NCHLT, as the GPU evaluations. Python onnxruntime 1.27.0, CPU.
- **Clips (public sets only):** the same 100 FLEURS test clips as R-0036/R-0037 (seed 1); 200 NCHLT unseen-sentence
  test clips (seed 1, drawn as R-0028 drew its 200).
- **Compare, same clips:** R-0035's greedy GPU predictions (runs/R-0035/legacy_greedy/eval_*/predictions.jsonl) and the
  demo's model today, R-0027 ONNX q8 (from Hugging Face Ntlakanipho/whisper-small-isixhosa, onnx/).

## Pass bars (Neon's, set before running; not to be changed after)
- **FLEURS 100:** candidate CER <= R-0035 greedy GPU CER + 0.50, AND at least 1.50 CER below R-0027 ONNX q8 on the same
  clips; 0 runaway loops after the loop guard.
- **NCHLT 200 unseen:** candidate CER <= R-0035 greedy GPU CER + 0.40.
- If A fails and B passes: the encoder is the 4-bit-sensitive part; the ~950 MB desktop-only option goes to the founder.
- **Browser step (only if a candidate passes):** Chrome/Edge WebGPU, transformers.js 4.3.2: a 12-15 s clip in <= 8.0 s
  warm, peak memory <= 2.5 GB, 5/5 runs succeed, same text as Python (<= 0.1 CER difference), download <= 600 MB
  (<= 1000 MB only if labelled desktop Wi-Fi only).

## Risks noted before running
- Laptop: 14.6 GB RAM (5.4 GB free at the start), 20 GB free disk. The export can peak at 8-12 GB RAM. If it fails,
  stop and ask the founder about Neon's ~$0.15 cloud CPU fallback (not spent without his word).

## Build notes (lead, 2026-11-20)
- Venv C:\Users\ntlak\venvs\onnx-med: torch 2.3.1+cpu, transformers 4.41.2, optimum 1.20.0, onnx 1.23.2, onnx-ir 1.1.0,
  onnxruntime 1.27.0, onnxslim, numpy 1.26.4, jiwer 3.0.5. Scripts: src/export_onnx_q4.py, src/eval_onnx_browser.py,
  src/tjs_float16.py (transformers.js 3.8.1's float16 converter, vendored unchanged).
- Four snags on the way (P-0026): merged fp32 decoder over 2 GB; onnxconverter-common cannot convert If branches;
  an onnxruntime CPU graph-optimisation bug on float16 copies (scored with basic optimisation); and `accuracy_level=4`
  (from the brief) made the q4f16 encoder output NaN. transformers.js leaves it unset; so do we now.
- Decoder inputs checked: no `cache_position` (P-0015 pin works).
- Files (C:\Users\ntlak\isixhosa-speech-ai-data\onnx\R-0035, not committed): encoder q4f16 180.91 MB, decoder merged
  q4f16 367.12 MB (A = 548.0 MB); encoder fp16 615.03 MB (B = 982.2 MB); encoder q4 210.09 MB, decoder q4 502.86 MB
  (C = 713.0 MB). Our decoder is ~31 MB larger than onnx-community's stock-medium one (336.28 MB); not looked into.
- Demo baseline: Hugging Face Ntlakanipho/whisper-small-isixhosa @ 24d2a1e1 onnx/ (R-0027 q8), same scorer.

## Outcome, candidate A (q4f16 + q4f16, 548 MB): FLEURS PASS, NCHLT FAIL by 0.06
Laptop CPU, onnxruntime 1.27.0, 8 threads, basic graph optimisation, greedy + gzip loop guard.

| Set (same clips) | A WER / CER | R-0035 GPU greedy | R-0027 q8 (demo today) | Bar | Result |
|---|---|---|---|---|---|
| FLEURS test, 100 (R-0036's) | 30.89 / **6.61** | 29.50 / 6.69 | 42.45 / 10.31 | CER <= 7.19 and <= 8.81 | PASS |
| NCHLT unseen, 200 (R-0028's) | 30.03 / **5.27** | 27.65 / 4.81 | (R-0028: 35.49 / 6.07) | CER <= 5.21 | **FAIL (+0.46)** |

Identical outputs to the GPU: 34/100 FLEURS, 166/200 NCHLT. Loop guard used 0 times; 0 runaways. CPU speed is not the
browser's (FLEURS 1446 s for 1281 s of audio). By the pre-set rule, candidate B is scored next; C (q4, float32 maths)
is scored on NCHLT to tell 4-bit weights from float16 maths.

## Outcome, candidates B and C, and verdict (lead, 2026-11-20 late)
The first B run was stopped by the 2 h tool limit after the laptop went to sleep at 19:04 (20/200 clips done); the
scorer now asks Windows to stay awake while it runs, and B was rerun from the start.

| Candidate (size) | FLEURS 100 CER | NCHLT 200 unseen CER | Identical to GPU (NCHLT) | Result |
|---|---|---|---|---|
| R-0035 GPU greedy (3 GB, reference) | 6.69 | 4.81 | - | - |
| A q4f16 + q4f16 (548 MB) | 6.61 PASS | 5.27 FAIL (+0.46) | 166 | FAIL |
| B fp16 encoder + q4f16 decoder (982 MB) | 6.75 PASS | 5.23 FAIL (+0.42) | 171 | FAIL |
| C q4 + q4, float32 maths (713 MB) | not run | 5.27 (+0.46) | 166 | (diagnostic) |
| R-0027 q8, the demo today (295 MB) | 10.31 | 6.07 (R-0028) | - | - |

WER: B FLEURS 31.14 / NCHLT 30.20; C NCHLT 30.03. 0 loop-guard uses, 0 runaways in every run.

**Verdict: FAILED the pre-set bar, narrowly, on NCHLT only.** No candidate goes to the browser step without the
founder's word.

What it shows:
- C = A exactly: float16 maths costs nothing; the loss is the 4-bit weights.
- B gains only 0.04 over A with a 430 MB bigger encoder: the encoder is not the sensitive part (Neon's #1 worry);
  the 4-bit decoder is.
- The loss is small and uneven: A is worse than the GPU on 22 of 200 NCHLT clips and better on 11, mostly short
  sentences from speaker 505 (the hardest speaker for every model). On FLEURS, A is level with the GPU.
- Against the demo's model today on the same clips, A is far better: FLEURS CER 6.61 vs 10.31, NCHLT 5.27 vs 6.07.
