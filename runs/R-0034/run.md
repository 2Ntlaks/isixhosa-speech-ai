# R-0034 · Thetha vs Meta Omnilingual CTC 300M and 1B (v2), same clips, same scoring

Before the run (drafted by the builder 2026-11-19; the lead fills in the outcome). Plan: D-0031, step 2.

- **Why:** Meta's Omnilingual ASR (Apache 2.0, Nov 2025) already covers isiXhosa (598.8 h of it in training). Its CTC
  models write every 20 ms slice of sound in parallel, with no 30 s window and no loops, so they are much faster on a
  CPU. R-0032 compared Thetha with Meta CTC 1B only on 100 FLEURS clips, through a private copy of a friend's project
  that no longer exists. Before spending more on Whisper, this run measures where Meta stands on all four test sets.
- **Models:** `omniASR_CTC_300M_v2` (325M parameters) and `omniASR_CTC_1B_v2` (975M), from Meta's official package
  `github.com/facebookresearch/omnilingual-asr` at commit `81f51e224ce9e74b02cc2a3eaf21b2d91d743455` (version 0.2.0,
  the first with the v2 models; PyPI only has 0.1.0, which does not know them). Own venv, Python 3.12, fairseq2 and the
  torch it asks for; the job checks the installed version is 0.2.0. Weights download from Meta's server on first use.
- **Evaluator:** `src/eval_omni.py`, through `ASRInferencePipeline(model_card=...)`. No language code is passed (CTC
  models do not use one). Clips are at most 30 s (the package refuses > 40 s). Same clip lists and the same
  `src/scoring.py` normalisation as Thetha (`src/testsets.py`).
- **Fairness adjustments (Neon's pre-flight memo, Q2):** curly apostrophes (U+2018, U+2019, U+02BC) are turned into
  the straight `'` before scoring (Thetha only writes `'`; otherwise the normaliser would split words at them); the
  unmapped score is reported too. Digits: FLEURS references contain digits in 200 of 1034 clips, and a spelled-out
  number counts as wrong, so FLEURS is also reported on the 834 clips whose reference has no digit. Also reported:
  CER without spaces (word-splitting differences), how many outputs contain digits or non-ASCII letters.
- **Accuracy:** GPU, the package's default bfloat16, every clip of the four test sets, alone on the GPU (after
  R-0033's GPU part). Each model first runs two batches of the longest real clips (~30 s) at batch 8; if that runs out
  of memory, batch 4, then 2, then 1 (the batch size used is recorded). Peak GPU memory is in every metrics.json.
- **Speed:** CPU only (GPU hidden), batch 1, 8 threads, **float32**, on the same 50 seeded clips per set that R-0033
  times R-0019-int8 on (200 clips), 1B first. bfloat16 only as a probe: 300M on 20 FLEURS clips, against float32 on
  the same 20 (Meta issue #57: bfloat16 can be much slower on CPUs without bfloat16 instructions, like this AMD EPYC).
  The CPU phase stops itself after 45 min. Warm-up and audio loading are not timed. Speeds are this node's, not the
  laptop's; only same-node numbers are compared.
- **Failures:** each set is a separate step; a failed or timed-out step is recorded (`FAILED_PARTS`) and the others
  still run. Meta's venv runs in a clean environment (no library path from the job's own venv, Neon review F-02).
- **Compared with:** R-0019 under the standard decoding (R-0033 beam 5 + guard, GPU float16) for accuracy; R-0019 int8
  CPU beam 5 + guard (R-0033) for speed.

## How the comparison is read (set before the run)
- **Training-data overlap (Neon's pre-flight memo, Q1; Meta does not publish its exact split list):**
  - **Fair, primary:** FLEURS test (both trained on FLEURS train; test held out for both), all 1034 and the 834
    digit-free clips; Soapies test (neither trained on it).
  - **Secondary, with a caveat:** Swivuriso dev_test **unscripted** (723 clips). Meta trained on African Next Voices;
    whether its training included dev_test speakers is unknown.
  - **Diagnostic only, not a fair benchmark:** Swivuriso dev_test **scripted** (1422 clips): the same prompts were read
    by speakers in every split and Thetha removed them from its training, Meta likely did not. NCHLT full test: Thetha
    trained on NCHLT and 81.6 % of test clips repeat training sentences. NCHLT is compared only on its **511
    unseen-sentence clips**, with the caveat that NCHLT's studio recordings are Thetha's home ground.
- **What would change the plan (a recommendation for the founder, not a rule):** if Meta 1B (GPU accuracy run,
  apostrophes mapped) is within 0.5 CER of R-0019 (R-0033, beam 5 + guard, GPU float16) or better on BOTH the 834
  FLEURS test clips whose reference has no digit AND all 391 Soapies test clips, and its **median seconds per clip
  pooled over the 200 timed clips** (CPU, float32, batch 1) is at most half R-0019-int8's median on the same 200 clips
  (beam 5 + guard, same node), the lead proposes trying a CTC fine-tune (Neon's step 5) before more Whisper runs;
  otherwise Whisper stays the main path and R-0035 goes ahead as planned. No model is published or replaced by this
  run.

## Command
Runs inside R-0033's node (`runs/R-0033/job.sh` calls `runs/R-0034/omni.sh setup`, `gpu`, `cpu`). On its own:
```
DISK_GB=150 FALLBACK_TYPES="g6.2xlarge" cloud/run_job.sh --run R-0034 --type g6.xlarge --market ondemand --max-hours 2
```
(Alone it writes straight to `out/`, so `cloud/collect.sh R-0034` puts the results in `runs/R-0034/`.)
- **Cost:** included in R-0033's estimate (its share: venv and weights ~10 min while R-0033 works, GPU accuracy
  ~15 min alone, CPU timing ~15-20 min, 45 min at most). Alone on a g6.xlarge ($0.805/h): ~1-1.5 h, ~$1.
- **Laptop checks (builder):** fairseq2 has no Windows build, so the package could not run on the laptop. Checked
  instead: the package's source at the pinned commit (input format, 40 s limit, CTC ignores the language code); the
  evaluator end to end in its dry-run mode on all four formats; a unit test with a stand-in pipeline (one mono 16 kHz
  float32 clip per call, Soapies resampled from 32 kHz, no language code, curly apostrophes mapped, raw output kept);
  the omni.sh phases rehearsed in dry-run mode. **The first real call happens in the job's 3-clip preflight.**
- Swivuriso and Soapies per-clip outputs stay out of git (gitignored), as for Thetha.
