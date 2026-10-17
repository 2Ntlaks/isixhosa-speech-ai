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
