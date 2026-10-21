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

## Handoff before model benchmarking

- Founder subsequently requested: "post pr and claiude will do that". Stop waiting for the audit; hand the
  paired model benchmark to Claude. The paired and long-recording benchmarks have **not run**. There is no
  measured latency or memory improvement to report yet, and real-model output equivalence is unverified.
- Implementation: `343e904`, with `src/live.py` unchanged since that commit. The reproducible baseline is
  `20b9468` in this branch, whose live.py is identical to the original local baseline `2dff2ea`.
- Changes: one 30-second chunk per model call by default, compatible feature reuse during comparisons,
  feature extraction and model loading inside the request lock, and comparison models loaded on first use.
  `--chunk-batch-size` and `--threads` allow explicit overrides. Beam 5 and token limits are unchanged.
- Expected benefit, not yet measured: lower model working memory for long recordings, less repeated feature
  extraction in comparisons, and lower startup cost when only the default model is used. First comparison
  now includes loading its model. Larger batches may be faster; full uploaded audio still occupies RAM.
- The earlier thread probe is retained as inconclusive evidence, not a speed claim or tuning decision.
  No training was performed; WER/CER for the new implementation remain pending. Cloud cost is $0.

### Claude: run these after the laptop audit finishes

Use this PR checkout as the current directory. Set `THETHA_ASSETS_ROOT` to the checkout containing the local
`data/` and `.venv/` directories if this is a worktree; omit the setting for a self-contained checkout.
Run each command to completion before starting the next. Do not run them alongside another inference job.

```powershell
$env:CT2_USE_MKL = '0'
$env:THETHA_ASSETS_ROOT = '<absolute path to checkout containing data and .venv>'
$python = Join-Path $env:THETHA_ASSETS_ROOT '.venv/Scripts/python.exe'
& $python -B runs/R-0025/validate_live.py
& $python -B runs/R-0025/validate_live.py --long baseline
& $python -B runs/R-0025/validate_live.py --long candidate
```

The first command alternates baseline/candidate order on 32 fixed NCHLT clips and shares one loaded model.
The latter commands must be separate processes: they compare peak process working set on a recording assembled
from dataset audio lasting at least 45 seconds. No transcripts are written. Check `validation.json` for 32/32
identical normalized hashes and equal WER/CER, then compare the hashes and scores in `long-*.json`.
Report wall-clock times and peak memory, including any regression. These are small engineering checks, not
new full-test accuracy results. Append results here and to results.md before making performance claims.

### Lightweight validation completed

`python -B -m unittest discover -s tests -v`: 7 tests passed (0.032 seconds of test execution, excluding imports).
These use fake models and cover chunk order/tails, batch bounds, feature reuse/isolation, the Transformers path,
failure recovery, queued-request serialization, HTTP response compatibility and public transcript-log privacy.
They do not establish real-model accuracy or performance. `git diff --check` also passed.
