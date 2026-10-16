# Journal

Append-only, newest at the bottom. One entry per working session, written by the agent that did the work.
Never edit or delete old entries; add a correction entry instead.

Format:

    ## YYYY-MM-DD HH:MM — <short title>
    - Agent/session: <which Claude Code session or account, if known>
    - Did: <what was done, in plain language>
    - Result: <numbers or outcome; link run IDs like R-0003 and problem IDs like P-0002>
    - Cost: <AWS $ spent this session, or $0>
    - Next: <what the next session should do>

## 2026-10-16 11:30 — Project created
- Agent/session: Claude Code (Mgaguli SA Studio session)
- Did: researched datasets and prior work; wrote SPEC.html, AGENTS.md, roadmap and end-product drawings;
  set up this evidence system (JOURNAL, results, problems, decisions, runs/, evidence/).
- Result: plan agreed in principle; founder reading the spec. Founder does not write code; agents do.
- Cost: $0
- Next: founder answers the three questions in SPEC §7; then stage 1 (baseline) on the laptop.

## 2026-10-16 19:00 — Data in the cloud
- Agent/session: Claude Code (isiXhosa Speech AI session, account2)
- Did: founder confirmed they speak isiXhosa (D-0003), chose cloud storage for datasets (D-0004, docs/data-flow.png)
  and accepted NCHLT CC BY 3.0 (D-0005). Found that SADiLaR serves NCHLT without a login, so no SADiLaR account
  is needed. Wrote cloud/fetch_data.sh + cloud/node/fetch_bootstrap.sh (small CPU node, self-terminating) and
  cloud/wait.sh. Ran jobs fetch-fleurs-1 and fetch-nchlt-1. Drew docs/stage1.png for the next stage.
- Result: s3://mgaguli-studio-render-<acct>/datasets/ holds 9.55 GB, 46 667 objects.
  fleurs_xh_za: train/dev/test .tsv + audio tar.gz (2.9 GB), ~3 min. nchlt_xho: zip MD5 matched SADiLaR
  (0e8918da0e1ac9acb3a300c7198c33dd), extracted to datasets/nchlt_xho/extracted/ (11 GB incl. local zip; zip itself
  not uploaded), ~15 min. Checksums in each MANIFEST.txt. NCHLT test set: 8 speakers (4 m, 4 f), 2 770 clips,
  many of them single words or short phrases. Problems P-0001 (no progress meter, fixed), P-0002 (SSM not set up).
- Cost: EC2 < $0.01 (two t3.small, ~20 min total); S3 ~ $0.23 one-off for uploads + ~ $0.22/month storage.
- Next: stage 1 baseline on the laptop (R-0001): fixed list of 100 test clips across the 8 speakers, stock
  whisper-small, WER + CER, samples.md for the founder to judge by ear. Fix P-0002 before stage 2.

## 2026-10-16 19:40 — Stage 1 baseline (R-0001)
- Agent/session: Claude Code (isiXhosa Speech AI session, account2)
- Did: founder asked to run stage 1 in the cloud instead of on the laptop (D-0006). Wrote src/nchlt.py,
  src/scoring.py (normalisation v1: drops NCHLT's [s] non-speech marker), src/baseline.py, requirements-gpu.txt,
  cloud/run_job.sh + cloud/node/job_bootstrap.sh (GPU job runner, ships the exact git commit), cloud/collect.sh.
  Dry-run tested locally (reference-as-guess scores 0 %). Ran R-0001 on the full NCHLT test set. Built the
  results page evidence/stage1-baseline.html (private artifact https://claude.ai/artifact/1jNv7cgnmtkWxGETkTYMTB).
  Updated docs/stage1.png for the cloud plan.
- Result: R-0001 WER 196.56 %, CER 75.09 %; 52 languages detected; 22 exact matches, all English prompts.
  Problems P-0003 (no spot capacity -> on-demand), P-0004 (CRLF in collect script).
- Cost: about $0.13 GPU (g6.xlarge on-demand, ~9.5 min). Day total about $0.40 incl. S3 uploads.
- Next: founder listens to data/listen/R-0001/ and answers the 3 questions on the results page. Fix P-0002 (SSM).
  Draw the stage 2 sheet (training loop, learning rate, checkpoints), then R-0002: first fine-tune of whisper-small on
  the NCHLT training set, same test set. Open choices to bring to the founder: language tag for isiXhosa
  (reuse an existing one vs add a new token), spot vs on-demand for a ~1-2 h run.
