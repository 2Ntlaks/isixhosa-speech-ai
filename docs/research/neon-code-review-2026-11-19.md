# Independent Code Review: R-0033, R-0034, and R-0035 (Branch `t3/81cf49f5`)

Date: 2026-11-19
Reviewer: Independent Review Sub-Agent (Neon)
Reviewed branch: `t3/81cf49f5` at commit `9decc4a` (`C:\Users\ntlak\.t3\worktrees\isixhosa-speech-ai\t3-81cf49f5-34573ff61965f22c`)
Diff base: `main` (`027c664`) - 23 files changed, +2,312 / -124 lines
Scope: Pre-spend review before launching R-0033 (loop-guarded re-score of R-0019), R-0034 (Meta Omnilingual CTC `300M_v2` / `1B_v2` vs Thetha), and R-0035 (`whisper-medium` retrained with the fixed recipe).

---

## 1. Executive Summary & Checklist Table

The core ML and scoring code (`src/testsets.py`, `src/train.py`, `src/eval_guarded.py`, `src/eval_omni.py`, `src/make_ct2.py`, `.gitignore`) is cleanly structured, well tested (34/34 unit tests pass), and faithful to the lead-adopted settings. However, **none of the three jobs is safe to spend on as written** because of **4 confirmed/high-risk blockers in the cloud job scripts** (a guaranteed crash on R-0035's expected evaluation resume path, a shared-library `LD_LIBRARY_PATH` leak from `.venv` into `/opt/omni-venv` paired with R-0034 setup failures aborting R-0033, 6 simultaneous GPU processes sharing a 22.04 GiB L4 with an unpreflighted `1B_v2` batch-8 run, and a repeat of P-0016's unguarded `curl` download with no stall timeout). All blockers are straightforward shell fixes.

### Review Checklist Summary

| # | Checklist Item | Verdict | Highest Severity | Key File:Line |
|---|---|---|---|---|
| 1 | Correctness & comparability (clips, normalisation, lead settings) | **PROBLEM** (core clips/norm OK; 2 telemetry/timing issues) | should-fix | `src/eval_guarded.py:177-197`, `src/compare_runs.py:74` |
| 2 | Leakage & Swivuriso dev stratification | **OK** | nit | `src/train.py:168-184, 322-340, 374-380` |
| 3 | SpecAugment (training-only, `attention_mask`, bf16/grad) | **OK** | nit | `src/train.py:99-108, 145-153, 208-213, 417-418`, `src/check_specaug.py:70-85` |
| 4 | Cloud safety, resume, log visibility, region, secrets, cost | **PROBLEM** | **blocker** | `runs/R-0035/job.sh:117-167`, `runs/R-0033/job.sh:24-89`, `cloud/node/test_data.sh:30-31, 81-83`, `runs/R-0034/omni.sh:23-60` |
| 5 | Pre-registered rules in `runs/R-003x/run.md` | **PROBLEM** (R-0033 Rule 1 not enforced in `job.sh`; 2 minor wording ambiguities) | should-fix | `runs/R-0033/job.sh:51-59`, `runs/R-0033/run.md:46`, `runs/R-0034/run.md:38-41` |
| 6 | Privacy (`.gitignore` for Swivuriso/Soapies, no audio/weights) | **OK** | nit | `.gitignore:24-28`, `src/compare_runs.py:74-75` |
| 7 | Anything else that would waste money or mislead | **PROBLEM** | should-fix | `runs/R-0033/run.md:55,59`, `runs/R-0034/omni.sh:50-60`, `runs/R-0035/job.sh:22` |

### Findings Ledger (All Issues)

| ID | Area | Verdict | Severity | Certainty | File:Line | Short Summary |
|---|---|---|---|---|---|---|
| F-01 | Cloud/Resume (R-0035) | PROBLEM | **blocker** | Confirmed bug | `runs/R-0035/job.sh:159,162,164-167` | Evaluation resume crashes with `tail` exit 1 because S3 sync excludes `gpu_fp16_beam5.*.log` |
| F-02 | Cloud/Isolation (R-0033/R-0034) | PROBLEM | **blocker** | Confirmed bug (high crash risk on Linux) | `cloud/node/test_data.sh:81-83`, `runs/R-0033/job.sh:24,43,61,70`, `runs/R-0034/omni.sh:10-36` | `setup_ct2` exports `.venv`'s `torch 2.5.1` `LD_LIBRARY_PATH` into `/opt/omni-venv`; R-0034 failure kills R-0033 |
| F-03 | Cloud/VRAM (R-0033/R-0034) | PROBLEM | **blocker** | Confirmed concurrency defect; OOM risk high | `runs/R-0033/job.sh:43-50,61,64-81`, `runs/R-0034/omni.sh:34,44`, `src/eval_omni.py:107` | 6 concurrent GPU processes on one 22.04 GiB L4; `1B_v2` `batch_size=8` never preflighted; R-0034 crash kills R-0033 |
| F-04 | Cloud/Stalls (All jobs) | PROBLEM | **blocker** | Confirmed bug (P-0016 repeat) | `cloud/node/test_data.sh:30-31`, `runs/R-0034/omni.sh:23-26,34,44` | `curl` fetching FLEURS (up to 2.6 GB) has no `--speed-limit`/`--speed-time`/resume; `omni.sh` installs/downloads have no timeout |
| F-05 | Cloud/Disk (R-0033/R-0034) | PROBLEM | should-fix | Confirmed from R-0012/R-0029 logs | `runs/R-0033/run.md:55,59`, `runs/R-0034/run.md:46` | Default `DISK_GB=100` (~96 GiB usable) risks `ENOSPC` with DLAMI + `.venv` (~56 GB) + `/opt/omni-venv` + `uv` cache + 10.5 GB models + data |
| F-06 | Cloud/Quota (R-0033) | PROBLEM | should-fix | Confirmed code + D-0026 quota | `runs/R-0033/run.md:55`, `cloud/run_job.sh:48` | `FALLBACK_TYPES="g6.4xlarge g6e.xlarge"` hits `VcpuLimitExceeded` (16 vCPU > 8 vCPU quota) and aborts before trying `g6e.xlarge` |
| F-07 | Rules/Cost (R-0033) | PROBLEM | should-fix | Confirmed bug | `runs/R-0033/job.sh:51-59` vs `runs/R-0033/run.md:42-43` | Reproduction check prints `DIFFERENT` and exits 0 instead of aborting, wasting ~2 h if Rule 1 fails |
| F-08 | Cloud/Visibility (All jobs) | PROBLEM | should-fix | Confirmed bug (P-0006 gap) | `runs/R-0033/job.sh:48-50,66-78,85-89`, `runs/R-0034/omni.sh:44-57`, `runs/R-0035/job.sh:82,85,154-172` | `| tail -n 1` and silent background logs hide eval progress from `node.log` for 6 to 25 min; `tail -n 4` truncates preflight errors |
| F-09 | Cloud/Durability (R-0035) | PROBLEM | should-fix | Confirmed bug | `runs/R-0035/job.sh:117-128, 134-135` | (a) `COMPLETE` written before syncing `out/model/` to S3; (b) `mirror || true` disables `set -e` so failed uploads still prune older S3 checkpoints |
| F-10 | Cost/Timing (R-0034 CPU) | PROBLEM | should-fix | Suspicion / high hardware risk | `runs/R-0034/omni.sh:50-60`, `runs/R-0033/run.md:63-65` | 200 clips of `omniASR_CTC_1B_v2` in `bfloat16` on AMD EPYC Zen 3 (no AVX-512 BF16) may run very slowly and threaten the 4 h cap |
| F-11 | Comparability (R-0033 vs R-0034) | PROBLEM | should-fix | Confirmed code asymmetry | `src/eval_guarded.py:177-186` vs `src/eval_omni.py:101-102` | `eval_omni.py` excludes warm-up from CPU timing; `eval_guarded.py` does not warm up before timing `clips[0]` |
| F-12 | Telemetry (R-0033) | PROBLEM | should-fix | Confirmed bug (verified in `faster-whisper 1.2.1`) | `src/eval_guarded.py:197, 212, 219` | Empty decoded output (`not text.strip()`) yields `segments == []` and is misreported as `no_speech_skip: True` even when `no_speech_threshold=None` |
| F-13 | Cost/Budget (R-0035) | PROBLEM | should-fix | Confirmed math | `runs/R-0035/run.md:65-80`, `cloud/run_job.sh:16`, `decisions.md:286` | Total R-0035 time (~6.0-6.3 h) likely hits 6 h cap; combined spend ($14-$17) exceeds D-0031's ~$10-$13; needs founder OK or trim |
| F-14 | Rules Clarity (R-0033/R-0034) | PROBLEM | should-fix | Confirmed text ambiguity | `runs/R-0033/run.md:46`, `runs/R-0034/run.md:38-41` | Rule 3 (pooled 200 vs per-50) and R-0034's 0.5 CER / 2x speed criteria (which FLEURS subset, which CPU dtype/stat) need 1-line clarification |
| F-15 | Cloud/Region (P-0019) | PROBLEM | should-fix | Confirmed omission | `cloud/node/test_data.sh`, `runs/R-0035/job.sh` | On-node scripts omit explicit `export AWS_DEFAULT_REGION=us-east-1` (rely on EC2 IMDS/default) |
| F-16 | Tooling (`compare_runs.py`) | PROBLEM | nit | Confirmed bug | `src/compare_runs.py:74` | Crashes with `FileNotFoundError` if first folder is an older `eval_soapies.py` or `eval_ct2.py` folder (no `samples.md`) |
| F-17 | Waste (R-0035) | PROBLEM | nit | Confirmed | `runs/R-0035/job.sh:22, 27-30` | Downloads `openai/whisper-medium` (3.06 GB) even on eval-only resume (`TRAINED=1`), and downloads FLEURS `test.tar.gz` twice on cold S3 |
| F-18 | Ops/Paths (R-0034) | PROBLEM | nit | Confirmed | `runs/R-0034/job.sh:9-10`, `runs/R-0033/run.md:56` | Standalone `R-0034/job.sh` writes `out/R-0034/...` -> `collect.sh` creates `runs/R-0034/R-0034/`; `R-0033/run.md` move note should copy contents |
| F-19 | Live Server (`live.py`) | PROBLEM | nit | Confirmed | `src/live.py:315, 327` | Startup warmup passes 1 s of silence while `VAD=True`, so Silero VAD returns `[]` and CT2 first-inference warmup is skipped until request 1 |
| F-20 | Defensive Checks | OK (minor) | nit | Confirmed | `src/train.py:333-334`, `runs/R-0035/job.sh:95-98`, `src/eval_guarded.py:195`, `src/check_specaug.py:70` | Un-re-normalised Swivuriso text compare; preflight checks subset of `data_split.json`; `fallback` assumes <=30 s; `check_specaug.py` uses `no_grad`/fp32 |

---

## 2. Verification of Lead-Adopted Settings

Every setting adopted by the lead was checked directly against the code:

| Adopted Setting | Implemented Value & Location | Verdict |
|---|---|---|
| `faster-whisper` `WhisperModel.transcribe` (not batched) | `WhisperModel(...)` + `model.transcribe(audio, **opts)` (`src/eval_guarded.py:136,183`) | OK |
| `language="sw"`, `task="transcribe"` | Defaults in `src/eval_guarded.py:49-50,73` | OK |
| `without_timestamps=True` | `not a.with_timestamps` -> `True` (`src/eval_guarded.py:63,78`) | OK |
| `condition_on_previous_text=False` | Default `False` (`src/eval_guarded.py:62,77`) | OK |
| `compression_ratio_threshold=2.4` | Default `2.4` (`src/eval_guarded.py:59,76`) | OK |
| `temperature=(0, 0.2, 0.4, 0.6)` | Default `"0.0,0.2,0.4,0.6"` -> `(0.0, 0.2, 0.4, 0.6)` (`src/eval_guarded.py:57,71,75`) | OK |
| `best_of=5` | Default `5` (`src/eval_guarded.py:52,73`) | OK |
| `log_prob_threshold=None`, `no_speech_threshold=None` | Both default `None` (`src/eval_guarded.py:60-61,76-77`) | OK |
| `repetition_penalty=1.0`, `no_repeat_ngram_size=0` | Defaults `1.0`, `0` (`src/eval_guarded.py:55-56,74-75`) | OK |
| `vad_filter=False` for test sets (on for live page) | `eval_guarded.py:65,79` default `False`; `live.py:306,315` default `True` | OK |
| `beam 1` and `beam 5` arms | `runs/R-0033/job.sh:65-76`, `runs/R-0035/job.sh:167,174` | OK |
| Omnilingual without `lang`, `< 40 s`, `U+2019` mapped | `src/eval_omni.py:38,67,74,81,103,115,119` (`lang=None`, `<= 30 s` + `<= 40 s` check, maps `U+2018`/`U+2019`/`U+02BC` -> `'`, logs unmapped score too) | OK |
| R-0035 SpecAugment (`time 0.05/10/min 2`, `feature 0.10/8/min 1`) + `attention_mask` | `runs/R-0035/job.sh:70-71`, `src/train.py:99-108,145-153,208-213,417-418,453` | OK |
| R-0035 `9000` steps, `lr 1e-5`, `warmup 500`, `linear` | `runs/R-0035/job.sh:68,131` | OK |
| R-0035 selection `0.5*Swivuriso dev CER + 0.5*FLEURS dev CER` | `CombinedTrainer` (`src/train.py:198-202,216-231,441,452-456`), `runs/R-0035/job.sh:69` | OK |
| R-0035 `generation_max_length=225` | `runs/R-0035/job.sh:68`, `src/train.py:262,449` | OK |

---

## 3. Detailed Review by Checklist Item

### Item 1: Correctness & Comparability - **PROBLEM (core clips/normalisation OK; 2 should-fix issues, 1 nit)**

**What is verified OK:**
- **Exact clip sets and counts (`src/testsets.py:65-95`):**
  - Swivuriso `dev_test`: loads `dev_test.tsv`, filters `duration <= 30.0`, uses `DEFAULT_MAX_NEW_TOKENS["swivuriso"] = 440` -> matches R-0019's `2,145` clips (`1,422` scripted / `723` unscripted, 24 speakers).
  - FLEURS `test`: `cloud/node/test_data.sh:10-51` pins `google/fleurs` commit `70bb2e84b976b7e960aa89f1c648e09c59f894dd`, verifies SHA-256 of each `.tar.gz`, asserts `1,034` clips `<= 30 s`, and uses `max_new_tokens = 225` -> matches R-0019 (`1,034` clips, `7` over 30 s).
  - NCHLT `test`: loads `nchlt_xho.tst.xml`, passes `SEEN="--train-xml $T/nchlt_xho.trn.xml --train-fleurs-tsv $F/train.tsv"` (`cloud/node/test_data.sh:77`, identical to `runs/R-0019/job.sh:60`), uses `max_new_tokens = 96` -> matches R-0019 (`2,770` clips: `2,259` seen / `511` unseen).
  - Soapies `engxho` test: loads `balanced_engxho.xml` + `engxho_tst_set_utterance_ids.txt`, resamples 32 kHz -> 16 kHz with `scipy.signal.resample_poly` identically to `src/eval_soapies.py:68-69`, computes identical `cer_no_spaces` and `word_hits` (`src/testsets.py:113-129`), and uses `max_new_tokens = 96` -> matches R-0030 (`391` clips, 5 speakers).
- **Normalisation:** Every evaluator scores through unchanged `src/scoring.py` `v1` (`normalise` and `score`). `eval_omni.py` maps curly apostrophes (`U+2018`, `U+2019`, `U+02BC` -> `'`) before `normalise()`, preserves `hyp_raw`, and logs `score_without_apostrophe_mapping` plus the 834 digit-free FLEURS subset (`src/testsets.py:153-155`).
- **`faster-whisper` windowing & token cap:** Verified directly in `faster-whisper 1.2.1` (`FeatureExtractor` and `generate_with_fallback`): for `<= 30.0 s` audio (`<= 480,000` samples), `content_frames <= 3000 == nb_max_frames`, so each clip runs in a single 30 s window; `len(prompt) + max_new_tokens = 4 + 440 = 444 <= 448` (`self.max_length`), so Swivuriso will not raise `ValueError`; `suppress_tokens=[-1]` matches OpenAI Whisper's non-speech symbol list (allowing inline apostrophes and hyphens).
- **`src/baseline.py` refactor:** Diff against `main` confirms `whisper_transcriber`, duration sorting, batching (`32`), and `metrics.json` fields match earlier runs verbatim.
- **CPU sample alignment:** Both `runs/R-0033/job.sh:86` and `runs/R-0034/omni.sh:57` call `testsets.load` with `--sample 50` and default `--sample-seed 1`, guaranteeing the exact same 50 clips per set (200 total).

**Problems found:**
- **[F-11, should-fix, confirmed] Missing warm-up in `src/eval_guarded.py:177-186` biases CPU timing vs `src/eval_omni.py:101-102`.**
  - Failure scenario: `eval_omni.py:101-102` runs an untimed warm-up on `clips[0]` (matching `runs/R-0034/run.md:23`), whereas `eval_guarded.py:177-186` starts `time.perf_counter()` immediately on `clips[0]` on a cold CTranslate2 engine. Over a 50-clip CPU sample, first-call threadpool/kernel initialization inflates Thetha's `seconds_per_clip_mean` and `p95` relative to Meta.
  - Fix: Run one untimed `list(model.transcribe(testsets.read16k(clips[0]["path"]), **opts)[0])` before `t0 = time.time()` in `eval_guarded.py` (clearing `log.attempts` afterwards).
- **[F-12, should-fix, confirmed] `src/eval_guarded.py:197, 212, 219` mislabels empty transcripts as `"no_speech_skip": True`.**
  - Failure scenario: Directly verified in `faster-whisper 1.2.1` (`transcribe.py` `generate_segments` line 246): `if segment["start"] == segment["end"] or not text.strip(): continue`. Whenever the model outputs empty text (e.g., on a noisy Soapies clip), `segments` is `[]` even though `no_speech_threshold` is `None`. `eval_guarded.py:197` sets `"no_speech_skip": not segments`, falsely incrementing `guard["no_speech_skipped"]` and misleading readers into thinking the disabled no-speech check fired.
  - Fix: Set `"no_speech_skip": opts["no_speech_threshold"] is not None and not segments` (and track `"empty_segments": not segments` separately if wanted).
- **[F-16, nit, confirmed] `src/compare_runs.py:74` crashes if the first folder came from `eval_soapies.py` or `eval_ct2.py`.**
  - Failure scenario: `src/compare_runs.py:7` claims support for older `eval_soapies.py`/`eval_ct2.py` folders, but line 74 unconditionally opens `os.path.join(first, "samples.md")`, which neither older script writes (confirmed: `runs/R-0030/R-0019/` contains only `metrics.json`). `tests/test_evaluators.py:178-186` missed this because it built its mock folder using `eval_omni.py --dry-run`.
  - Fix: Check `if os.path.isfile(samples_path):` before reading `samples.md`.

---

### Item 2: Leakage & Stratified Swivuriso Dev Subset - **OK (minor nits only)**

- **Speaker isolation (confirmed OK):**
  - Swivuriso `train` (407 speakers), `dev` (24 speakers), and `dev_test` (24 speakers) are speaker-disjoint splits from `src/swivuriso.py`, and `data/swiv_long/pieces.tsv` was extracted strictly from `train-*` parquet shards (`src/swivuriso_long.py:65,124`).
  - `src/train.py:380` explicitly asserts zero speaker overlap between `swiv_dev` and `train`.
- **Sentence isolation (confirmed OK):**
  - `runs/R-0035/job.sh:47-60` collects normalised sentences from NCHLT test, FLEURS `dev` + `test`, and Swivuriso `dev` + `dev_test` into `data/test_texts.txt`.
  - `src/train.py:325-339` fails closed if `--exclude-texts` is empty, unions `test_texts` with held-out NCHLT `dev_texts` and `--swivuriso-dev-tsv`, removes every matching clip from `data/swiv_all_train.tsv` (both short clips and long-clip pieces), and asserts zero overlap (`line 339`). Note also that `src/swivuriso_long.py:48-51,89` already dropped entire long clips containing any 3+-word test/dev sentence when cutting `pieces.tsv` in R-0027.
  - `runs/R-0035/job.sh:95-98` asserts exact parity with `runs/R-0029/model/data_split.json` (`swivuriso_train_clips: 52960`, `swivuriso_dropped_test_sentences: 6139`, `fleurs_train_clips: 3434`, `swivuriso_train_hours: 245.44`, `fleurs_train_hours: 13.03`).
- **Stratified Swivuriso dev subset (`src/train.py:168-184, 374-380`, confirmed OK):**
  - Filters `dev.tsv` to `duration <= 30.0` and reference token length `<= 220` (`4 prefix + 220 + 1 eos = 225 == generation_max_length`, so zero dev reference truncation).
  - Iterates over all sorted dev speakers (all 24), shuffles `unscripted` and `scripted` deterministically with `seed=42`, takes up to `per_speaker // 2` (`11`) unscripted, fills remaining up to `22` from scripted, and tops back up from unscripted if scripted runs short (e.g., 20+2 when a speaker has only 2 scripted clips). Verified for all edge cases including `per_speaker=1` (preflight) and small speakers.
- **Nits [F-20]:** `src/train.py:333-334` compares raw `c["text"]` against `test_texts` assuming Swivuriso TSVs are already normalised (true for `swivuriso.py`/`swivuriso_long.py`, but wrapping in `normalise(c["text"])` is more defensive); `runs/R-0035/job.sh:95-98` checks the preflight `data_split.json` (where `--train-longest 16` overwrote `train_clips`), so full `train_clips == 98663` / `train_hours == 309.68` is only verified manually after training starts.

---

### Item 3: SpecAugment (Training Only, `attention_mask`, bf16/Grad) - **OK (minor nits only)**

Directly verified against installed `transformers==4.46.3` in `.venv` (`modeling_whisper.py`, `WhisperFeatureExtractor`, and a live synthetic `WhisperForConditionalGeneration` forward+backward test):
- **Active in training only (confirmed OK):** `WhisperModel._mask_input_features` checks both `self.config.apply_spec_augment` and `self.training`. `Seq2SeqTrainer.evaluation_loop` calls `model.eval()` before loss and `generate()`, so masking is completely disabled during dev evaluation. (Note: `model/final/config.json` saves `apply_spec_augment: true`, which is safe because `baseline.py:36` and `live.py:85` call `.eval()` and CTranslate2 ignores it.)
- **`attention_mask` reaches the model and bounds time masks (confirmed OK):**
  - `Clips.__getitem__` (`src/train.py:99-108`) passes `return_attention_mask=True` ONLY on `train_dataset` (eval datasets keep `attention_mask=False`, avoiding any interference with `generate()`).
  - `Collator` (`src/train.py:146-147`) pads `input_features` and `attention_mask` together via `feature_extractor.pad(..., return_tensors="pt")` -> verified shape `(batch, 3000)`, dtype `torch.int32`.
  - `Seq2SeqTrainingArguments` sets `remove_unused_columns=False` (`src/train.py:450`), `WhisperForConditionalGeneration.forward` accepts `attention_mask` and forwards it to `self.model(..., attention_mask=attention_mask)` -> `_mask_input_features` -> `_compute_mask_indices`.
  - Verified `_compute_mask_indices` across clip lengths from 1 frame (0.01 s) to 3000 frames (30 s): never crashes even on ultra-short clips, and for all clips `>= 10` frames (0.10 s) places 100% of time masks strictly inside the clip's real audio frames.
- **bf16 and gradient behavior (confirmed OK):**
  - Directly tested `WhisperForConditionalGeneration` with `apply_spec_augment=True`, `mask_time_prob=0.05/10/2`, `mask_feature_prob=0.10/8/1`, `attention_mask`, `torch.amp.autocast(..., dtype=torch.bfloat16)`, and `loss.backward()`, for both `gradient_checkpointing=False` and `gradient_checkpointing=True`: both produced finite losses and finite gradients on every parameter with no autograd in-place error (in-place `input_features[mask] = 0` runs on a non-grad leaf input before `encoder.conv1`).
  - Also verified `CombinedTrainer` + `resume_from_checkpoint` + `load_best_model_at_end=True` on a multi-eval `eval_dataset` dict in `transformers 4.46.3`: `Trainer._evaluate` calls `self.evaluate(ignore_keys=...)` with `eval_dataset=None, metric_key_prefix="eval"`, `CombinedTrainer.evaluate` injects and logs `eval_combined_cer` before `Trainer._save_checkpoint` checks `metric_for_best_model="combined_cer"`, and resuming across checkpoints preserves the earlier best checkpoint cleanly. (Note: on PyTorch >= 2.6, `transformers 4.46.3` checkpoint resume hits `weights_only=True` in `torch.load(rng_file)`, which does NOT affect cloud nodes because `requirements-gpu.txt` pins `torch==2.5.1`.)
- **Nit [F-20]:** `src/check_specaug.py:42,70` tests in `float32` under `torch.no_grad()`, so it proves `attention_mask` routing and mask bounds but relies on `runs/R-0035/job.sh` preflight 2/3 (`train.py` for 2 real steps) to test `bf16` + backward on the L40S GPU.

---

### Item 4: Cloud Safety, Resume, Visibility, Region, Secrets, and Cost - **PROBLEM (4 blockers, 6 should-fix)**

#### Hard `--max-hours` cap & self-termination: **OK**
- `cloud/run_job.sh:16,43` caps `--max-hours <= 6` and sets `--instance-initiated-shutdown-behavior terminate`.
- `cloud/node/job_bootstrap.sh:7,11,28` schedules `shutdown -h +"$MAXMIN"` as the first command on boot and calls `finish()` -> `shutdown -h now` on both `DONE` and `FAILED`.
- No path leaves an instance running indefinitely beyond `--max-hours`. However, hanging until `--max-hours` wastes up to $3.91 (R-0033) or $13.44 (R-0035).

#### Secrets: **OK**
- Scanned the entire diff of all 23 files for tokens, keys, passwords, and AWS account IDs: zero matches.

#### Blockers in Cloud Scripts:

1. **[F-01, BLOCKER, confirmed bug] R-0035 evaluation resume crashes immediately (`runs/R-0035/job.sh:159, 162, 164-167`).**
   - Failure scenario: `runs/R-0035/run.md:76` expects total wall time of ~5.9-6.2 h against the 6 h cap, so Node 1 finishes training + `guarded 5` and is cut off during `legacy_greedy` or `guarded 1`. Node 2 launches (`TRAINED=1`), downloads test data + `models/R-0035/`, and runs line 164-165: `aws s3 sync "s3://$BUCKET/jobs/R-0035/out/" out/ --only-show-errors --exclude "*" --include "gpu_fp16_beam*/*" --include "legacy_greedy/*"`. Because of the `/` in `gpu_fp16_beam*/*`, S3 syncs `out/gpu_fp16_beam5/eval_*/metrics.json` but **skips `out/gpu_fp16_beam5.*.log`** (written at line 159 with a dot, no slash). Then line 167 calls `guarded 5`: all 4 sets already have `metrics.json` and hit `continue`, creating zero `.log` files. Line 162 executes `tail -q -n 1 out/gpu_fp16_beam5.*.log`; bash passes the unmatched literal glob to `tail`, which exits 1 (`No such file or directory`), and `set -euo pipefail` aborts Node 2 before `legacy_greedy` or `guarded 1` runs (~15-20 min L40S wasted per retry).
   - Fix: In `guarded()`, guard line 162 with `[ ${#pids[@]} -gt 0 ] && tail -q -n 1 out/gpu_fp16_beam$1.*.log` (and capture `fail=0; for p in "${pids[@]}"; do wait $p || fail=1; done` before returning `$fail` so a failed lane's log is still printed).

2. **[F-02, BLOCKER, confirmed bug] `setup_ct2()` exports `.venv`'s `LD_LIBRARY_PATH` into `/opt/omni-venv` (`cloud/node/test_data.sh:81-83` -> `runs/R-0033/job.sh:24,43,61,70` -> `runs/R-0034/omni.sh`).**
   - Failure scenario: `R-0033/job.sh:24` calls `setup_ct2`, which runs `export LD_LIBRARY_PATH="$libs:${LD_LIBRARY_PATH:-}"` pointing to `.venv`'s `torch==2.5.1` (`cu124` cuBLAS 12.4 / cuDNN 9.1). `R-0033/job.sh:43,70` then invokes `runs/R-0034/omni.sh`, which installs `omnilingual-asr==0.2.0` + `fairseq2` + its own newer `torch` in `/opt/omni-venv`. Because Linux `LD_LIBRARY_PATH` overrides ELF `RUNPATH`, `/opt/omni-venv/bin/python` loads `.venv`'s older `libcublas.so.12`/`libcudnn.so.9`, risking `ImportError` / `undefined symbol` / `CUDNN_STATUS_VERSION_MISMATCH` during `omni.sh setup` preflight. Because `R-0033/job.sh:61` does `wait $OMNI || { ... exit 1; }`, that aborts all of R-0033 after ~35 min of compute.
   - Fix: Add `unset LD_LIBRARY_PATH` at the top of `runs/R-0034/omni.sh`, and decouple R-0034 failures from R-0033 (see F-03).

3. **[F-03, BLOCKER, confirmed concurrency defect / high OOM risk] Six simultaneous GPU processes on one 22.04 GiB L4 + unpreflighted `1B_v2` `batch_size=8` + R-0034 failures kill R-0033 (`runs/R-0033/job.sh:43-50, 61, 64-81`, `runs/R-0034/omni.sh:34, 44`, `src/eval_omni.py:107`).**
   - Failure scenario:
     1. An AWS L4 GPU has **22.04 GiB** usable VRAM (confirmed in `problems.md` P-0007). `runs/R-0033/job.sh:70-76` launches **5** separate `faster-whisper` `whisper-medium` fp16 processes (~2.5-2.9 GiB each = ~12.5-14.5 GiB, including 5 CUDA/cuDNN contexts) at the exact same time as `omni.sh gpu`, which runs `omniASR_CTC_1B_v2` (975M params, ~3 GiB at batch=1) at `--batch-size 8`. Because `src/eval_omni.py:107` sorts clips shortest-first, `1B_v2` hits 8 simultaneous 28-30 s waveforms (conv feature maps + 48 transformer layers + 10,288-class CTC logits = ~5-9+ GiB) near the very end of Swivuriso, pushing total VRAM to ~17.5-23.5+ GiB and risking a late CUDA OOM after 30+ min.
     2. `omni.sh:34` only preflights `300M_v2` at `batch=3` (not `1B_v2` at `batch=8`) and runs that GPU preflight concurrently with `baseline.py` (`repro_greedy`, batch 32 on 440-token Swivuriso, ~8-10 GiB).
     3. `R-0033/job.sh:61` and `81` abort all of R-0033 whenever R-0034 fails (even though `R-0034/run.md:54` notes R-0034 has never been run on real hardware yet).
   - Fix: Run `omni.sh gpu` sequentially (it only takes ~5-10 min on GPU), limit R-0033 to 2-3 concurrent GPU lanes on L4 (plenty to saturate 58 SMs at ~6-8 GiB VRAM), preflight `1B_v2` at its real batch size (or use `--batch-size 4` for `1B_v2`), and isolate R-0034 errors (`OMNI_OK=0`) so R-0033 always completes and uploads its results.

4. **[F-04, BLOCKER, confirmed bug (P-0016 repeat)] `curl` in `cloud/node/test_data.sh:30-31` has no stall timeout, and `omni.sh` network steps have no timeouts.**
   - Failure scenario: `cloud/node/test_data.sh:30-31` runs `curl -sSfL --retry 5 -o ...` with NO `--speed-limit`, `--speed-time`, `--connect-timeout`, `--max-time`, or `-C -` resume (the exact bug documented in P-0016 and fixed in `cloud/node/fetch_bootstrap.sh:27-29`). A silent stall downloading `train.tar.gz` (~1.9 GB) or `test.tar.gz` (~0.6 GB) on a GPU node hangs until the 4 h ($3.91) or 6 h ($11.17-$13.44) cap. Likewise, `runs/R-0034/omni.sh:23-26,34,44` (`apt-get`, `uv pip install git+...`, Meta weight downloads from `dl.fbaipublicfiles.com`) lack `timeout` guards.
   - Fix: Copy `fetch_bootstrap.sh:27-29`'s stall-guarded resume helper (`--connect-timeout 30 --speed-limit 10000 --speed-time 120 -C -` in a retry loop with 60 s size logging) into `cloud/node/test_data.sh`, and wrap `omni.sh`'s `apt-get`, `uv pip install`, and preflight calls in `timeout` bounds.

#### Should-Fix Cloud Safety, Durability, and Cost Issues:

5. **[F-05, should-fix, confirmed] Default 100 GB root disk is tight for R-0033 + R-0034 (`runs/R-0033/run.md:55,59`).**
   - Evidence from `runs/R-0012/node.log:11` and `runs/R-0029/node.log:18`: the Ubuntu 24.04 DLAMI + `.venv` (`torch 2.5.1+cu124`) + `uv` cache already consume **~55-57 GB** before job data. Adding `/opt/omni-venv` (a second full PyTorch+CUDA+fairseq2 venv + `uv` cache, ~8-12 GB), `models_cache` (~5.5-8.5 GB), Meta's two checkpoints (`1.3 + 3.7 = 5.0 GiB` + temp download), and test audio (~3.3 GB) reaches **~83-90+ GiB** on a ~96 GiB formatted 100 GB disk. `runs/R-0033/run.md:59` underestimates Meta's models + venv as "5 GB" total.
   - Fix: Set `DISK_GB=150` in `runs/R-0033/run.md:55` (and `runs/R-0034/run.md:46`); adds < $0.01 to a 3-4 h run.

6. **[F-06, should-fix, confirmed] `FALLBACK_TYPES="g6.4xlarge g6e.xlarge"` can abort launch under the 8-vCPU G-instance quota (`runs/R-0033/run.md:55`, `cloud/run_job.sh:48`).**
   - `decisions.md` D-0026 records an 8-vCPU G-instance quota (32-vCPU request was PENDING). If `g6.2xlarge` has no capacity and quota is still 8 vCPUs, `g6.4xlarge` (16 vCPUs) returns `VcpuLimitExceeded`, which `cloud/run_job.sh:48` does NOT match (`InsufficientInstanceCapacity|Unsupported|MaxSpotInstanceCountExceeded`), aborting launch before trying `g6e.xlarge` (4 vCPUs).
   - Fix: Use `FALLBACK_TYPES="g6e.xlarge g6e.2xlarge"` (or verify the 32-vCPU quota and add `VcpuLimitExceeded` to `cloud/run_job.sh:48`).

7. **[F-08, should-fix, confirmed (P-0006 gap)] Evaluation progress is invisible in `node.log` for 6 to 25 minutes.**
   - R-0035 **training** (`runs/R-0035/job.sh:131-132`) IS visible within ~40 s (`logging_steps=25`, `PYTHONUNBUFFERED=1`, `grep --line-buffered`).
   - However, almost every evaluation step suppresses progress:
     - `runs/R-0033/job.sh:48-50` (`repro_greedy`, ~15-22 min) and `85-89` (CPU timing, ~25-30 min) pipe through `| quiet | tail -n 1`, printing nothing until each whole test set finishes.
     - `runs/R-0033/job.sh:66-78` (GPU lanes, ~35-55 min) redirects all logs to files and only prints one `nvidia-smi` line every 300 s (5 min).
     - `runs/R-0034/omni.sh:44-45,56-57` pipes through `| quiet | tail -n 1`, swallowing every 100-clip progress line.
     - `runs/R-0035/job.sh:82,85` (preflight 2/3) pipes through `| quiet | tail -n 4` (hiding progress and truncating real tracebacks if batch 8 fails for a non-OOM reason); lines `154-162` (`guarded` evals, ~25 min + ~12 min) have no monitor at all; lines `170-172` (`legacy_greedy`, ~8 min) pipe through `| tail -n 1`.
   - Fix: Replace `| tail -n 1` with `| tee out/<step>.log` on foreground evals, poll every 60 s (showing latest clip progress lines from `out/*.log`) during background evals, and capture full preflight 2/3 output to a log file printed on error.

8. **[F-09, should-fix, confirmed bugs] Two checkpoint/metadata durability flaws in `runs/R-0035/job.sh:117-128, 134-135`.**
   - (a) Lines 134-135 copy `model/log_history.json` and `model/data_split.json` to `out/model/` and immediately write `$MODELS/R-0035/COMPLETE` without syncing `out/model/` to S3 first. If the 6 h hard `shutdown -h` fires in the up-to-5-minute window before `job_bootstrap.sh:14` syncs `out/`, Node 2 sees `COMPLETE` (`TRAINED=1`), skips training, and `out/model/data_split.json` / `log_history.json` are lost from S3 `out/model/`.
   - (b) Line 128 runs `mirror || true`, which disables `set -e` inside the entire `mirror()` function in bash. If `aws s3 sync "$d"` fails transiently after `Trainer` rotated out an older local checkpoint, lines 124-126 still execute and delete the older S3 checkpoint before the newer one is uploaded.
   - Fix: (a) Explicitly sync `out/model/` and `out/train.log` to `s3://$BUCKET/jobs/R-0035/out/` BEFORE writing `$MODELS/R-0035/COMPLETE`; (b) inside `mirror()`, return 1 immediately if any `aws s3 sync`/`cp` fails so pruning only runs after all local checkpoints are confirmed in S3.

9. **[F-13, should-fix, confirmed math] Cost & wall-time check vs `cloud/run_job.sh`'s 6 h cap and D-0031's ~$10-$13 budget.**
   - **R-0035 check:** Measured R-0019 throughput is 1.64 s/step (`g6e.xlarge`, $1.861/h) and R-0029 is 1.57 s/step (`g6e.2xlarge`, $2.24/h).
     - Training 9,000 steps: `4.10 h` (`g6e.xlarge`) / `3.93 h` (`g6e.2xlarge`).
     - 9 dev evals (~68 s NCHLT 600 + ~95-110 s FLEURS 441 at 225 tok + ~55-70 s Swivuriso ~528 at 225 tok = ~3.7-4.1 min x 9): `~0.58-0.62 h`.
     - Boot/data/preflight: `~0.55-0.65 h`.
     - Post-training save, CT2 conversions, and 3 eval suites (`guarded 5`, `legacy_greedy`, `guarded 1`): `~0.75-0.90 h`.
     - **Total: `~6.0-6.3 h`** against the 6 h cap (`cloud/run_job.sh:16`), making a relaunch likely (~$11.50-$13.00 on `g6e.xlarge`, ~$14-$15 on `g6e.2xlarge`). The builder's estimate in `runs/R-0035/run.md:65-80` is honest and accurate.
   - **R-0033 + R-0034 check:** Builder's ~2-2.5 h (~$2.00-$2.50 on `g6.2xlarge` at $0.978/h; 4 h cap = $3.91 max) is reasonable **except** for: (a) `repro_greedy` on L4 (memory-bandwidth bound at ~300 GB/s vs L40S 864 GB/s -> ~19-22 min rather than 15-18 min), and (b) `omniASR_CTC_1B_v2` `bfloat16` on AMD EPYC Zen 3 CPU (see F-10 below, which could add 50-100 min and threaten the 4 h cap).
   - **Combined spend ($14-$17) exceeds D-0031's ~$10-$13 estimate.** Confirm founder approval for R-0035's revised cost (per `JOURNAL.md:411`) or adopt one of the trims noted in `runs/R-0035/run.md:79` (e.g., 8,000 steps = 2.59 epochs saves ~27 min and fits cleanly inside one 6 h node without relaunch overhead; dropping `beam-1` on R-0035 saves another ~12-15 min).

10. **[F-15, should-fix, confirmed] Explicit `--region us-east-1` / `AWS_DEFAULT_REGION=us-east-1` missing from on-node scripts (P-0019).**
    - Laptop scripts (`cloud/{run_job,wait,collect,fetch_data}.sh`) all export `AWS_DEFAULT_REGION=us-east-1`, but `cloud/node/test_data.sh` and `runs/R-0035/job.sh` rely on EC2 IMDS/default S3 region. Add `export AWS_DEFAULT_REGION=us-east-1` at the top of `cloud/node/test_data.sh`.

---

### Item 5: Pre-Registered Rules in `runs/R-003x/run.md` - **PROBLEM (1 enforcement bug, 2 wording clarifications)**

- **Stated before results & fair:** Yes. All three `run.md` plans are drafted before compute starts, and R-0035's ship rule (must beat R-0019 on both Swivuriso CER and FLEURS CER at 2 decimals under the same beam-5 guarded decoding, with NCHLT CER <= +0.5, and matching R-0029's training data counts) is fair and unambiguous.
- **[F-07, should-fix, confirmed bug] `runs/R-0033/job.sh:51-59` does not abort when Rule 1 fails.**
  - Failure scenario: `runs/R-0033/run.md:42-43` states that if the reproduction check fails on any set, nothing else from R-0033 is interpreted. Yet `runs/R-0033/job.sh:51-59` only prints `DIFFERENT: check data and model` and exits 0, spending another ~1.5-2 h (~$1.50-$2.00) on uninterpretable runs.
  - Fix: Exit non-zero (`sys.exit(1)`) if any of the 3 sets is outside tolerance.
- **[F-14, should-fix, confirmed wording ambiguity] Tighten two pre-registered criteria before launch:**
  - `runs/R-0033/run.md:46` Rule 3: clarify whether "on the 200 timed clips, the int8 CPU copy's CER is at most 0.3 above the GPU float16 beam-5 CER" is evaluated **pooled across all 200 clips** or **separately on each 50-clip set** (4 separate folders are produced, and 50 Soapies clips have high variance).
  - `runs/R-0034/run.md:38-41`: clarify which FLEURS CER (full 1,034 clips curly-mapped vs 834 digit-free) and which CPU speed metric (faster of `float32`/`bfloat16`, median vs mean, pooled vs per set) apply to the "within 0.5 CER ... and at least 2x faster" recommendation trigger.

---

### Item 6: Privacy & `.gitignore` - **OK (minor nit)**

- Tested `.gitignore` directly with `git check-ignore` against all 17 planned output paths across `runs/R-0033/`, `runs/R-0033/R-0034/`, `runs/R-0034/`, and `runs/R-0035/`:
  - Every `eval_swivuriso*/predictions.jsonl`, `eval_swivuriso*/samples.md`, `eval_soapies*/predictions.jsonl`, and `eval_soapies*/samples.md` is ignored.
  - Only `metrics.json` (aggregates + clip IDs only, zero transcript text) and NCHLT/FLEURS predictions remain commitable.
- Verified `eval_guarded.py`, `eval_omni.py`, `baseline.py`, `testsets.py`, `train.py`, and `compare_runs.py`: none logs Swivuriso or Soapies transcript text to stdout or `metrics.json`, and `compare_runs.py:75` restricts embedded sample tables strictly to `| nchlt_` and `| fleurs_`.
- `.gitignore` blocks `data/`, `checkpoints/`, `*.wav`, `*.flac`, `*.mp3`, `*.safetensors`, `*.bin`, `.env`. (Nit: `*.pt` and `*.onnx` are not in `.gitignore`, though no job writes them to `out/`.)

---

### Item 7: Anything Else That Would Waste Money or Mislead - **PROBLEM (1 should-fix, 3 nits)**

- **[F-10, should-fix, suspicion / high hardware risk] `omniASR_CTC_1B_v2` `bfloat16` across 200 clips on AMD EPYC Zen 3 CPU (`runs/R-0034/omni.sh:50-60`).**
  - Concrete failure scenario: `g6.2xlarge` uses AMD EPYC 7R13 (Zen 3 / Milan), which lacks native AVX-512 BF16 instructions. PyTorch CPU `bfloat16` falls back to software conversion/emulation and can run 3-10x slower than `float32`. Running 200 full clips of `1B_v2` in `bfloat16` (plus reloading the 3.7 GiB checkpoint 4 times per dtype = 8 loads of `1B_v2` and 8 loads of `300M_v2`) could take 50-100+ min on its own and hit R-0033's 4 h cap, cutting off the final timing runs.
  - Fix: Run all 50 clips/set for `float32` (expected winner on CPU per Meta Issue #57), and cap `bfloat16` to a quick check (e.g., 10 clips/set = 40 clips) to confirm the `float32` vs `bfloat16` ratio without risking the 4 h cap.
- **[F-17, nit, confirmed] Minor redundant downloads in `runs/R-0035/job.sh:22, 27-30`.**
  - Line 22 downloads `openai/whisper-medium` (3.06 GB) unconditionally, even on an eval-only resume (`TRAINED=1`) where `$BASE` is never used. Move line 22 inside `if [ $TRAINED = 0 ]`.
  - Lines 27 and 30 download FLEURS `test.tar.gz` (~600 MB) twice if FLEURS is not yet cached in S3 (`get_test_sets` calls `get_fleurs test`, then line 30 calls `get_fleurs train dev test`). Calling `get_fleurs train dev test` first (or skipping downloads when the local `.tar.gz` already matches `FLEURS_SHA`) avoids the duplicate transfer.
- **[F-18, nit, confirmed] Minor path ergonomics for R-0034.**
  - Running `runs/R-0034/job.sh` standalone writes under `out/R-0034/`, so `cloud/collect.sh R-0034` creates `runs/R-0034/R-0034/`. And `runs/R-0033/run.md:56` ("move `runs/R-0033/R-0034/` to `runs/R-0034/`") should note moving its *contents* (`mv runs/R-0033/R-0034/* runs/R-0034/`) since `runs/R-0034/` already exists.
- **[F-19, nit, confirmed] `src/live.py:327` warmup skips CTranslate2 first-inference init when `VAD=True`.**
  - `src/live.py:327` passes 1 s of zeros (`np.zeros(SR, dtype=np.float32)`) after line 315 sets `VAD=True`. Silero VAD returns `[]`, so weights and Silero load at startup, but CTranslate2's first-inference warmup does not run until the first user recording.

---

## 4. Read-Only Local Verification Performed

All checks were strictly local and read-only (no edits to either checkout, no network/AWS/training calls, `PYTHONDONTWRITEBYTECODE=1`):
- `git diff main...t3/81cf49f5`: inspected all 23 changed files line by line; confirmed worktree is clean.
- Python syntax (`ast.parse` on all 24 `.py` files in `src/` and `tests/`): **24/24 OK**.
- Shell syntax & line endings (`Git Bash -n` and `git ls-files --eol` on all 5 new `.sh` files): **5/5 pass `bash -n`, all LF (no CR bytes)**.
- Unit tests (`tests/` via worktree `.venv` Python 3.12.10, `transformers 4.46.3`, `faster-whisper 1.2.1`, `ctranslate2 4.5.0`): **34/34 OK**.
- Direct library checks in `.venv`:
  - `transformers 4.46.3`: verified `WhisperForConditionalGeneration.forward`, `WhisperModel._mask_input_features`, `_compute_mask_indices` (clip lengths 1..3000 frames), `WhisperFeatureExtractor.pad`, `bf16` autocast + `backward()` with `gradient_checkpointing` both `False` and `True`, and full `CombinedTrainer` + `resume_from_checkpoint` + `load_best_model_at_end` loop.
  - `faster-whisper 1.2.1` & `ctranslate2 4.5.0`: verified `WhisperModel.transcribe` defaults, `FeatureExtractor` 30.0 s boundary (`content_frames=3000`), `generate_with_fallback`, `generate_segments` (uncovered F-12), `non_speech_tokens`, and `ctranslate2/__init__.py` (`pkg_resources` is Windows-only, safe on Linux).
- `.gitignore`: verified 17 planned R-0033/R-0034/R-0035 output paths via `git check-ignore`.

---

## 5. Final Verdict: Safe to Spend?

| Job | Safe to Spend Right Now? | Minimum Fixes Required Before Launch |
|---|---|---|
| **R-0033** (`runs/R-0033/job.sh`, combined node) | **NO** | 1. Add stall-timeout + resume to `curl` in `cloud/node/test_data.sh:30-31` (**F-04**).<br>2. Isolate `LD_LIBRARY_PATH` from `runs/R-0034/omni.sh` (**F-02**) and decouple R-0034 errors so they never abort R-0033 (**F-03**).<br>3. Run `omni.sh gpu` sequentially and cap R-0033 concurrent GPU lanes to 2-3 on L4 (**F-03**).<br>4. Bump launch command to `DISK_GB=150` (**F-05**) and replace `g6.4xlarge` fallback with `g6e.xlarge g6e.2xlarge` (**F-06**).<br>5. Make `repro_check` exit 1 on failure (**F-07**), add 1-clip warm-up (**F-11**) and fix `no_speech_skip` (**F-12**) in `eval_guarded.py`, restore <1 min log visibility (**F-08**), export `AWS_DEFAULT_REGION=us-east-1` (**F-15**), and clarify Rule 3 (**F-14**). |
| **R-0034** (`runs/R-0034/omni.sh`, `runs/R-0034/job.sh`) | **NO** | 1. Fix `test_data.sh` `curl` stall timeout (**F-04**) and add `timeout` wrappers around `omni.sh` installs/downloads (**F-04**).<br>2. Add `unset LD_LIBRARY_PATH` at top of `omni.sh` (**F-02**).<br>3. Preflight `omniASR_CTC_1B_v2` at its actual GPU batch size (or drop `1B_v2` to `--batch-size 4`) and run GPU phase sequentially (**F-03**).<br>4. Trim CPU `bfloat16` sample (e.g., 10 clips/set) so Zen 3 emulated BF16 cannot exhaust the 4 h cap (**F-10**), set `DISK_GB=150` (**F-05**), restore log visibility (**F-08**), and clarify `run.md` decision thresholds (**F-14**). |
| **R-0035** (`runs/R-0035/job.sh`, `src/train.py`) | **NO** (ML code is **YES**; job script is **NO**) | 1. Fix `guarded()` resume crash on missing `out/gpu_fp16_beam5.*.log` (**F-01**).<br>2. Fix `test_data.sh` `curl` stall timeout (**F-04**).<br>3. Sync `out/model/` and `out/train.log` to S3 before writing `MODELS/R-0035/COMPLETE`, and stop `mirror()` from pruning S3 checkpoints when an upload fails (**F-09**).<br>4. Restore <1 min log visibility during `guarded()`/`legacy_greedy`/preflight (**F-08**), export `AWS_DEFAULT_REGION=us-east-1` (**F-15**), and skip base-model download when `TRAINED=1` (**F-17**).<br>5. Get founder OK on revised $14-$17 combined spend (or trim to 8,000 steps / drop R-0035 `beam-1` arm so it finishes inside one 6 h node without relaunching) (**F-13**). |
