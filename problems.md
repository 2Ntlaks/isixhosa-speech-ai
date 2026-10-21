# Problems

Every error, failure or surprise worth remembering: the raw material for the "what went wrong" part of the write-up.
Append-only. Keep the exact error text.

Format:

    ## P-0001 · YYYY-MM-DD · <short title>
    - Stage / run: <stage N, R-00xx>
    - Symptom: <what we saw; exact error message in a code block>
    - Cause: <why it happened, in plain language>
    - Fix: <what changed; commit or file>
    - Cost: <time lost, $ lost>
    - Lesson: <one sentence the founder could say in an interview>

## P-0001 · 2026-10-16 · Download job showed no progress for 15 minutes
- Stage / run: data download, job fetch-nchlt-1 (no run ID)
- Symptom: node.log stayed on `--- 16:37:55 nchlt.speech.corpus.xho.zip` with no percentage; founder asked "how far now?" and we could only guess.
- Cause: curl ran silent (`-sS`) and nothing else reported bytes received; we also cannot log in to the node (see P-0002).
- Fix: cloud/node/fetch_bootstrap.sh now logs the size downloaded so far every 60 s.
- Cost: none in $; some uncertainty.
- Lesson: any long cloud job must report its own progress, because you can't always look inside the machine.

## P-0002 · 2026-10-16 · SSM Session Manager cannot reach our nodes
- Stage / run: data download (both jobs)
- Symptom: console log on boot:
  ```
  SSM Agent unable to acquire credentials: ... AccessDeniedException: Systems Manager's instance management role is not configured for account: <acct>
  ```
- Cause: the node role (mgaguli-render-node) only allows S3 access to the bucket; the account has no SSM default host management role, and the role lacks AmazonSSMManagedInstanceCore.
- Fix: not yet. Harmless for downloads; needed before stage 2 so agents can look inside GPU nodes without opening SSH.
- Cost: none.
- Lesson: decide how you'll get inside a cloud machine before you need to.

## P-0003 · 2026-10-16 · No spot GPU capacity anywhere in us-east-1
- Stage / run: stage 1, R-0001 (first launch attempt)
- Symptom: `cloud/run_job.sh --run R-0001` tried g6.xlarge, g5.xlarge and g4dn.xlarge spot in all 6 zones:
  ```
  no GPU capacity anywhere right now (spot)
  ```
- Cause: AWS had no spare discounted (spot) GPU machines of those types at that moment. Not a quota problem:
  both the spot and on-demand G-instance quotas are 8 vCPU.
- Fix: relaunched with `--market ondemand` (g6.xlarge, ~$0.80/h instead of ~$0.35-0.50/h spot); got capacity in the 4th zone.
- Cost: ~2 min; a few tens of cents more than spot for this short run.
- Lesson: spot is cheap but not guaranteed; short jobs can just go on-demand, long training runs need checkpoints to survive either way.

## P-0004 · 2026-10-16 · Collect script could not find files that were in S3
- Stage / run: stage 1, R-0001 (after the run)
- Symptom:
  ```
  fatal error: An error occurred (404) when calling the HeadObject operation: Key "jobs/R-0001/out/baseline.log" does not exist
  ```
- Cause: on Windows the aws tool ends every output line with an invisible carriage return (CRLF), so the file name
  read back had a hidden character on the end and S3 said it didn't exist.
- Fix: cloud/collect.sh strips `\r` from the listing.
- Cost: ~5 min, $0.
- Lesson: when scripts pass text between Windows and Linux tools, invisible line-ending characters break exact names.

## P-0002 update · 2026-10-17 · SSM fixed
- Fix: attached the AWS managed policy AmazonSSMManagedInstanceCore to role mgaguli-render-node (shared with the
  Studio render nodes, which now get SSM too). Verified on R-0002's node i-03c416a8b6fb0af97: registered "Online"
  about 1 minute after boot; `aws ssm send-command` ran nvidia-smi / df / tail on it. No ports opened.
- How agents look inside a node now: `aws ssm send-command --document-name AWS-RunShellScript ...` then
  `aws ssm get-command-invocation` (or `aws ssm start-session` with the Session Manager plugin, installed locally).

## P-0005 · 2026-10-17 · Training crashed: missing `accelerate` package
- Stage / run: stage 2, R-0002 attempt 1 (smoke test)
- Symptom:
  ```
  ImportError: Using the `Trainer` with `PyTorch` requires `accelerate>=0.26.0`: Please run `pip install transformers[torch]` or `pip install 'accelerate>={ACCELERATE_MIN_VERSION}'`
  ```
- Cause: the Hugging Face Trainer needs a helper library (accelerate) that isn't installed with transformers by
  default. requirements-gpu.txt listed only what the stage 1 evaluator needed.
- Fix: accelerate==1.1.1 pinned in requirements-gpu.txt. New runs/preflight.sh trains 2 steps on 4 speakers before the
  full data download, so this kind of error shows up ~3 min after boot. A local CPU test was tried first but torch
  would not install on Windows under the long scratch path (files silently missing, `DLL load failed while importing _C`).
- Cost: ~8 min GPU, about $0.11.
- Lesson: this is exactly what a smoke test is for; the cheapest place to find a bug is the smallest run.

## P-0006 · 2026-10-17 · Training progress invisible in the log
- Stage / run: stage 2, R-0004
- Symptom: 6 minutes into training, node.log and out/train.log had no step counter or loss lines, while the GPU
  showed 100 % use (checked over SSM: `0 /opt/work/out/train.log`).
- Cause: job.sh pipes training output through `grep -vE ... | tee`. When grep writes into a pipe it buffers its output
  in blocks instead of passing each line on, so lines arrive in large chunks, late.
- Fix: for this run, watch the checkpoints in S3 instead (each trainer_state.json holds the dev score). For future runs,
  use `grep --line-buffered` and `PYTHONUNBUFFERED=1`.
- Cost: none; visibility only.
- Lesson: check that a long job's progress is visible during the first minute, not after.

## P-0007 · 2026-10-17 · whisper-medium does not fit the L4 GPU; my smoke test's last check used the wrong set-up
- Stage / run: stage 3, R-0008
- Symptom:
  ```
  torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 94.00 MiB. GPU 0 has a total capacity of 22.04 GiB of which 35.12 MiB is free. Including non-PyTorch memory, this process has 21.99 GiB memory in use.
  ```
  at batch 16 x 2 and at batch 8 x 4. Only gradient checkpointing fit (17.4 GB) and it was slow (~9 s/step, ~10 h for a full run).
  The two-dev-set check then ran at batch 8 x 4 *without* checkpointing, ran out of memory, and stopped the job.
- Cause: training needs weights, gradients and two Adam averages per weight (~12 GB for 769M parameters in fp32)
  plus activations for 30 s of audio per clip. The last check's settings were mine: I didn't reuse the set-up that fit.
- Fix: R-0009 on a 48 GB L40S (D-0012); every part of the smoke test now uses the same batch set-up.
- Cost: ~$0.20.
- Lesson: when a smoke test finds the set-up that fits, every later step must use it; and model memory scales with
  parameters x ~16 bytes before any data.

## P-0008 · 2026-10-17 · whisper-medium ran out of memory even on a 48 GB GPU (smoke test tried one set-up only)
- Stage / run: stage 3, R-0009
- Symptom:
  ```
  torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 94.00 MiB. GPU 0 has a total capacity of 44.39 GiB of which 61.31 MiB is free.
  ```
  at batch 16 x 2 without gradient checkpointing on the L40S.
- Cause: activations for 16 clips x 30 s of audio through 24 encoder + 24 decoder layers are larger than I estimated
  (on top of ~12 GB for weights, gradients and optimiser state). And the smoke test tried only that one set-up, so a
  "no" ended the run instead of moving on to the next option: the same mistake as P-0007.
- Fix: R-0010 tries both remaining set-ups in one run and keeps the faster one that fits.
- Cost: ~$0.30.
- Lesson: a smoke test is for answering "which set-up?", so it should try every candidate, not stop at the first failure.

## P-0009 · 2026-10-17 · No L40S GPU free anywhere in us-east-1 at launch time
- Stage / run: stage 3, R-0012
- Symptom: `cloud/run_job.sh` tried g6e.xlarge on-demand in all 6 default subnets and ended with
  `no GPU capacity anywhere right now (ondemand)` (InsufficientInstanceCapacity), although R-0010 got one an hour earlier.
- Cause: AWS had no spare L40S machines of that size at that moment. Capacity for newer GPU types comes and goes.
- Fix: a retry loop (same machine type, every 3 minutes, up to 45 minutes); it launched at the next try. No other
  machine type was used, so speed and cost stayed as approved.
- Cost: nothing (failed launches are free); ~5 minutes.
- Lesson: for scarce GPU types, retry the same type before changing the plan; a different type would change cost or memory.

## P-0010 · 2026-10-17 · Comparison tool mixed up runs whose folders have the same name
- Stage / run: stage 3, R-0012 analysis
- Symptom: `src/compare_runs.py runs/R-0012/eval_fleurs runs/R-0007/eval_fleurs ...` reported only 2 runs instead of 4;
  the first entry was named eval_fleurs and showed stock medium's scores (45.86) instead of R-0012's.
- Cause: runs were named by the last folder name, so three folders called eval_fleurs overwrote each other.
- Fix: runs are now named by the run ID in their path (R-0012), and the tool stops if two folders still collide.
  Caught before any number was recorded.
- Cost: nothing; ~5 minutes.
- Lesson: when a report shows fewer rows than inputs, stop and find out why before reading the numbers.

## P-0011 · 2026-10-17 · Live page server stopped: laptop ran low on memory
- Stage / run: live page (src/live.py, D-0014)
- Symptom: the background server was stopped by Claude Code ("stopped because the system is running low on memory");
  the page showed "server not running".
- Cause: both models loaded at full precision in one process (medium ~3.5 GB + small ~1.3 GB) on a 15 GB laptop that
  also runs a browser and other apps.
- Fix: one model per server by default, loaded in bfloat16 (medium 1.9 GB); then CTranslate2 int8 copies (R-0013):
  medium ~0.8 GB + small ~0.25 GB, both loaded together.
- Cost: nothing; ~10 minutes; no recordings lost.
- Lesson: on the laptop, check free memory before loading a model; size the model format to the machine.

## P-0012 · 2026-10-17 · Shortening Whisper's 30 s window to speed it up broke the output
- Stage / run: live page speed work (before R-0013)
- Symptom: encoding only the recorded audio (+1 to 3 s) instead of the full padded 30 s gave repeated words:
  CER 488 % (+3 s) and 838 % (+1 s) on the 20 listening clips, against 3.16 % with the full window.
- Cause: Whisper (and our fine-tunes) were only ever trained on 30 s windows; the decoder relies on the padding.
  The whisper.cpp "audio_ctx" trick needs a model trained or tuned for shorter windows.
- Fix: not used; the full window stays. Speed came from the int8 engine instead (R-0013).
- Cost: nothing; ~5 minutes.
- Lesson: speed tricks are experiments too: measure accuracy before shipping them.

## P-0013 · 2026-10-19 · Two laptop jobs stopped: laptop ran low on memory again
- Stage / run: R-0014 (stock whisper-medium on the Soapies test) and the CPU smoke test of the stage 4 training code
- Symptom: Claude Code stopped both background jobs ("stopped because the system is running low on memory"). Stock
  medium had scored 100 of 391 clips (very slow: ~16 s per clip); the smoke test had built its data (2206 clips incl.
  83 English and 40 stitched) but never reported a training step. Free memory had dropped to ~0.85 GB of 15 GB.
- Cause: the agent ran two heavy jobs at once: a medium model scoring clips (~1.7 GB) and a training test whose data
  loader starts 4 extra Python processes (~0.4 GB each), which also scores 536 Soapies dev clips at every evaluation,
  next to the founder's browser and other apps. Both also competed for the same 8 CPU cores.
- Fix: none needed in code; nothing lost (R-0007 and R-0012 results were already saved). Re-run one job at a time,
  smoke test with fewer dev clips / no extra loader processes. Not restarted automatically (waits for the founder).
- Cost: $0; ~25 minutes of laptop time.
- Lesson: on the laptop, one heavy job at a time; check free memory first (P-0011 again).

## P-0014 · 2026-10-19 · Hugging Face refused the demo Space: free Docker Spaces now need PRO
- Stage / run: open-sourcing (D-0019), release/publish.py, step 3 (the Space)
- Symptom: both model repos uploaded fine (3.84 GB, 1.22 GB, public); creating the Space failed with
  "402 Client Error: Payment Required ... Static Spaces are free for everyone, but hosting Gradio and Docker Spaces on
  free cpu-basic requires a PRO subscription."
- Cause: the agent's knowledge of Hugging Face's free tier was out of date; it told the founder the demo would be free
  without checking the current terms first.
- Fix: model cards re-uploaded without the demo link (it pointed at a Space that did not exist). Demo options go to the
  founder: PRO ($9/month), an in-browser static demo (free), or no online demo.
- Cost: $0; ~5 minutes.
- Lesson: check a service's current pricing before promising "free"; the Hub API's 402 text is the source of truth.

## P-0015 · 2026-10-19 · In-browser model: two export problems
- Stage / run: R-0017 (ONNX copy of R-0007 for transformers.js, D-0020)
- Symptom 1: the page downloaded the model, then failed: "An error occurred during model execution: "Missing the
  following inputs: cache_position." Cause: optimum 1.21+/1.23 with transformers >= 4.42 export Whisper's decoder with a
  cache_position input that transformers.js 3.0.2 does not supply. Fix: export with transformers 4.41.2 + optimum 1.20.0.
- Symptom 2: that export's 8-bit decoder was 316 MB instead of ~195 MB. Cause: the output layer reuses the word-embedding
  table through a Transpose, which dynamic quantisation skips, so a 159 MB float32 copy stayed. Fix: store the
  transposed table as its own weight before quantising (decoder 197 MB). Accuracy re-measured on the final files.
- Also: without cross-origin isolation the browser ran the model on one thread (~18 s per short clip). Serving
  transformers.js and its wasm from the Space itself, plus COOP/COEP headers in the Space config, made it ~7 s.
- Cost: $0; ~1.5 hours.
- Lesson: test the exact files in the target runtime (a real browser), not only in Python; export versions matter.

## P-0016 · 2026-10-21 · NCHLT auxiliary download stalled at 8.0 GB; base datasets had to be re-fetched
- What: job fetch-aux-1 (t3.small) downloaded xho-aux1.zip (9.39 GB) from SADiLaR at ~1 GB/min, then the log showed
  "xho-aux1.zip: 8.0G so far" every minute from 06:22 to 06:28 UTC with no growth. curl had retries but no stall
  timeout, so it would have waited until the 3 h shutdown cap.
- Cause: the transfer hung without failing (server or network side; not investigated further). `curl --retry` only
  retries after an error, never on a silent stall.
- Fix: get() in cloud/node/fetch_bootstrap.sh now passes --speed-limit 10000 --speed-time 120 and loops up to 6 times
  with -C - (resume), so a stall aborts after 2 min and continues where it stopped. Stopped the stuck node by hand and
  relaunched as fetch-aux-2.
- Also found: NCHLT, FLEURS and Soapies had been deleted from S3 on 2026-10-19 (project stopped, D-0018), so training
  needed them re-fetched (job fetch-base-2, ~15 min, checksums verified as before).
- Cost: ~$0.01 of node time; ~10 minutes.
- Lesson: any long download needs a stall timeout, not just retries; check S3 for the inputs before planning a run.

## P-0017 · 2026-10-21 · NCHLT auxiliary zip will not unpack
- What: fetch-aux-2 downloaded xho-aux1.zip in full (MD5 matches SADiLaR's published 09fa14f3...), then unzip failed:
  "warning [xho-aux1.zip]: 5088485238 extra bytes at beginning or within zipfile ... error [xho-aux1.zip]: start of
  central directory not found; zipfile corrupt."
- Cause (likely, not yet confirmed): the 9.4 GB archive was written without proper ZIP64 records, so its directory
  offsets wrap past 4 GB; the file is as published, the archive format is the problem.
- Fix: not done yet. Next attempt: read it with a tool that walks the local headers instead of the central directory
  (bsdtar/libarchive or 7-Zip), on a cloud node.
- Cost: ~$0.01; not blocking (R-0019 did not use it).
- Lesson: a matching checksum proves the download, not that the archive is readable; test-unpack early.

## P-0018 · 2026-10-21 · Concurrent sessions shared a run ID and CPU
- What: the inference optimization plan initially used R-0022. Another session replaced that plan with its
  decode audit and committed in the same checkout. Its inference process was also present during the thread
  probe. There was no exception message: this was a coordination failure, not a Python failure.
- Cause: the sessions shared a checkout, run-number namespace and laptop, without an exclusive reservation.
- Fix: isolated the optimization in a managed worktree, moved its evidence to R-0025, and preserved the other
  session's audit. Treat the thread timings as inconclusive and keep the thread default unchanged. The founder
  confirmed that the paired benchmark could use the CPU after the audit finished.
- Cost: $0 cloud. The discarded sweep contains 276.2 seconds of timed decoding, plus unmeasured setup overhead.
- Lesson: separate checkouts prevent file collisions; CPU scheduling and sequential run IDs still need coordination.
