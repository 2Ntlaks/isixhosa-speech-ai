# R-0037 · Why did R-0035's int8 copy miss on FLEURS? (laptop, same 100 clips as R-0036)

Before the run (lead, 2026-11-20). Diagnostic, $0 (laptop CPU), set after R-0036's FLEURS miss (+0.35 vs +0.3 allowed).

Same 100 FLEURS test clips (seed 1), same decoding (beam 5 + loop guard), same laptop and ctranslate2 4.8.1:
1. **R-0019-int8** (published ct2-int8, HF 603a39b5): today's Thetha default. Does R-0035-int8 still beat it?
2. **R-0035 at full precision on the CPU** (float32, converted from S3 models/R-0035): is the gap the int8 copy (float32
   close to the GPU's 5.97) or the CPU/library (float32 also near 6.3)?

Nothing here changes R-0036's verdict. The founder decides what to do with the answers; the 0.3 rule is not rewritten.
