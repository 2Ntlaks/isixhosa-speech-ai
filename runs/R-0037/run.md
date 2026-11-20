# R-0037 · Why did R-0035's int8 copy miss on FLEURS? (laptop, same 100 clips as R-0036)

Before the run (lead, 2026-11-20). Diagnostic, $0 (laptop CPU), set after R-0036's FLEURS miss (+0.35 vs +0.3 allowed).

Same 100 FLEURS test clips (seed 1), same decoding (beam 5 + loop guard), same laptop and ctranslate2 4.8.1:
1. **R-0019-int8** (published ct2-int8, HF 603a39b5): today's Thetha default. Does R-0035-int8 still beat it?
2. **R-0035 at full precision on the CPU** (float32, converted from S3 models/R-0035): is the gap the int8 copy (float32
   close to the GPU's 5.97) or the CPU/library (float32 also near 6.3)?

Nothing here changes R-0036's verdict. The founder decides what to do with the answers; the 0.3 rule is not rewritten.

Note (during the run): the float32 conversion failed on the laptop with ctranslate2 4.8.1 + transformers 4.46.3
(`TypeError: WhisperForConditionalGeneration.__init__() got an unexpected keyword argument 'dtype'`). The laptop was
moved to ctranslate2 4.5.0 (the cloud's version), and a third arm added before rerunning: **R-0035-int8 again with
ctranslate2 4.5.0**, which tests the library version directly.

## Outcome (lead, 2026-11-20)
Same 100 FLEURS test clips (seed 1), beam 5 + loop guard, laptop CPU 8 threads (CT2_USE_MKL=0):

| Arm | WER | CER | Same text as R-0035 GPU | Decode s (1281 s audio) |
|---|---|---|---|---|
| R-0035 int8, ctranslate2 4.8.1 (R-0036) | 28.43 | 6.32 | 63 | 770 |
| R-0035 int8, ctranslate2 4.5.0 | 28.43 | 6.16 | 65 | 772 |
| R-0035 float32, ctranslate2 4.5.0 | 27.73 | 5.94 | 98 | 1237 |
| R-0035 float16 GPU (cloud, R-0035) | 27.73 | 5.97 | 100 | 80 |
| R-0019 int8, ctranslate2 4.8.1 (today's Thetha) | 31.46 | 7.06 | 20 | 702 |
| R-0019 float16 GPU (cloud, R-0033) | 30.83 | 6.85 | 22 | 150 |

Reading:
- **The CPU is not the cause:** float32 on the laptop gives the GPU's text on 98 of 100 clips (5.94 vs 5.97).
- **The int8 copy costs ~0.2-0.35 CER on FLEURS** (+0.19 with ctranslate2 4.5.0, +0.35 with 4.8.1; WER the same in
  both). The library version moves it by 0.16, so the R-0036 miss (+0.35 vs 0.3 allowed) is at the noise edge of a
  100-clip sample; with the cloud's library it is inside the rule. R-0019's own int8 copy costs a similar +0.21.
- **For Thetha users the comparison that matters:** R-0035 int8 (6.16-6.32) beats today's R-0019 int8 (7.06) on the
  same clips and library, and even beats R-0019 at full precision on the GPU (6.85).
- R-0036's verdict stays as recorded (FAIL on FLEURS under the rule as written). Whether to switch Thetha's default
  anyway, with ctranslate2 pinned to 4.5.0, goes to the founder.
- Laptop now has ctranslate2 4.5.0 and transformers 4.46.3 (the cloud's versions).
