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
