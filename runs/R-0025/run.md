# R-0025: CPU inference profiling and bounded live inference

- Date: 2026-10-21. Founder authorized inference optimization and a PR.
- Baseline: live.py at 2dff2ea, including beam 5 and public-log privacy. Same source as 22f9568.
- Machine: Windows, AMD Ryzen 7 PRO 250, 8 physical / 16 logical cores, approximately 16 GB RAM.
- Model: local R-0019-int8, CTranslate2 4.5.0, CT2_USE_MKL=0. No AWS or training.
- Planned before work: thread sweep 1/2/4/8 on six seed-22 samples from R-0021; validate on 32 seed-22 samples
  plus a multi-chunk recording assembled only from their dataset audio. Same beam 5, sw tag, 225-token limit,
  normalization, model weights and 30-second boundaries. No transcript content in benchmark artifacts.
- Pass: identical normalized outputs on the validation sample; demonstrate lower latency or bounded feature/model
  working memory, report WER/CER and any throughput tradeoff. No claim of full-corpus equivalence.
- Before-work drawing: docs/inference-plan.png (vector source alongside it).
- Thread probe command: `$env:CT2_USE_MKL='0'; .venv/Scripts/python.exe -B runs/R-0025/profile_threads.py`.
- Evidence relocation: this work initially reserved R-0022. A concurrent session replaced that plan with its
  candidate audit and committed in the shared checkout. The optimization files and measurements were moved to
  an isolated managed worktree and R-0025. Its own audio/data changes were left untouched. See P-0018.
- Probe limitation: the other session started an inference process during this work. Thread timing results may
  overlap that work and are not reliable evidence for a new default. All four settings produced the same scores
  on six clips (WER 38.89%, CER 6.85%). Retain the original eight-thread default on this laptop.
- The founder confirmed the CPU would be left free after the audit. No more inference is started until it ends.
- Cost: $0 cloud. Validation commands and outcomes will be appended below.
