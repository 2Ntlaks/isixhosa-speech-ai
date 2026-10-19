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

## 2026-10-17 12:00 — Stage 2: first fine-tune works (R-0002, R-0003, R-0004)
- Agent/session: Claude Code (isiXhosa Speech AI session, account2)
- Did: founder chose the Swahili tag (D-0007) and on-demand GPUs (D-0008). Fixed SSM access to nodes (P-0002).
  Wrote src/train.py (Hugging Face Seq2SeqTrainer, 6 dev speakers held out, resume from checkpoints), runs/preflight.sh,
  src/compare_runs.py, seen/unseen-sentence scoring in src/baseline.py. Found that 1 444 of 2 066 test sentences (82 % of
  test clips) also occur in training. Smoke test R-0002 failed once (P-0005, missing accelerate) then passed
  (resume works, 1.65 s/step). Ran R-0003 (stock + forced <|sw|>) and R-0004 (4000 steps) on one node.
  Drew docs/stage2.png; wrote docs/progress.html (plain-language progress page for the founder).
- Result: R-0003 CER 45.70 / WER 164.46. **R-0004 test CER 2.98 / WER 16.63; unseen sentences CER 6.2 / WER 36.6;
  64.5 % of clips exact.** Dev CER plateaued from step 3000 (3.6 %); training loss steps down at each pass (memorisation).
  Problems P-0005 (accelerate), P-0006 (grep buffering hid progress).
- Cost: R-0002 $0.11 + $0.16, R-0003+R-0004 ~$1.85 (2.3 h g6.xlarge on-demand). Project total so far ~ $2.50.
  S3 now also holds models/R-0004 (1 GB) and checkpoints under jobs/ (expire after 30 days).
- Next: results page for R-0004; founder listens to the same 20 clips. Stage 3 plan, one change per run: add FLEURS
  (more varied, full sentences), whisper-medium, real <|xh|> tag, augmentation, compare with Meta MMS; keep the
  unseen-sentence score as the headline.

## 2026-10-17 15:10 — Stage 3, experiment 1: adding FLEURS (R-0005, R-0006, R-0007)
- Agent/session: Claude Code (isiXhosa Speech AI session, account2)
- Did: founder approved (D-0009) and asked for a reviewer sub-agent. Wrote src/fleurs.py, FLEURS support in
  src/baseline.py and src/train.py, runs/R-0007/job.sh. A separate reviewer agent checked the code before launch: no
  crash, but two fairness problems, both fixed (FLEURS text normalised for training, D-0010; NCHLT generation limit kept
  at 96). Ran R-0005, R-0006, R-0007 on one on-demand node; progress now visible live (P-0006 fixed).
- Result: FLEURS test (all unseen sentences): R-0006 stock+tag CER 65.45 / WER 185.34; R-0005 (NCHLT-only model)
  29.81 / 94.86 (glues words); **R-0007 (NCHLT+FLEURS) 10.16 / 44.38**. NCHLT test R-0007 2.91 / 16.80 (R-0004
  2.98 / 16.63); NCHLT unseen 5.8 / 34.9 (R-0004 6.2 / 36.6). Best model so far: R-0007.
- Cost: ~$1.97 (2.45 h g6.xlarge on-demand). Project total ~ $4.50.
- Next: results page; founder listens. Stage 3 options: whisper-medium on NCHLT+FLEURS; add a FLEURS dev set to pick
  checkpoints; give FLEURS more weight; real <|xh|> tag; Meta MMS comparison.

## 2026-10-17 19:55 — Stage 3, experiment 2: whisper-medium (R-0008 to R-0012)
- Agent/session: Claude Code (isiXhosa Speech AI session, account2)
- Did: founder chose whisper-medium (D-0011). Added FLEURS dev tracking (information only) and gradient checkpointing to
  src/train.py. Smoke tests: R-0008 on the L4 showed medium fits only with checkpointing at ~9 s/step (P-0007), so the
  founder chose the 48 GB L40S (D-0012); R-0009 ran out of memory at batch 16 x 2 (P-0008); R-0010 tried both remaining
  set-ups and found batch 8 x 4 without checkpointing fits (32.8 GB). Added a DISK_GB option to cloud/run_job.sh
  (medium checkpoints are 8.6 GB). Founder approved the full run with the October budget consequence (D-0013). No L40S
  free at first (P-0009); retried and launched. Fixed a naming bug in src/compare_runs.py (P-0010).
- Result: stock medium + tag (R-0011): NCHLT CER 33.74 / WER 137.21, FLEURS 45.86 / 142.32. **R-0012 (medium, NCHLT +
  FLEURS): FLEURS test CER 8.03 / WER 37.83 (R-0007 10.16 / 44.38); NCHLT test CER 2.33 / WER 12.71 (R-0007 2.91 /
  16.80); NCHLT unseen sentences CER 5.0 / WER 28.7 (R-0007 5.8 / 34.9).** Better on every measure. Best model: R-0012.
  Training ran at 1.52 s/step, much faster than the smoke test suggested, so the run took 2.3 h instead of 3.7 h.
- Cost: R-0008 $0.20, R-0009 $0.30, R-0010 $0.50, R-0011 + R-0012 ~$4.34. Project total ~ $9.85. October EC2 compute
  for the mgaguli-gpu-monthly brake should land near $17 of $20 once billing catches up.
- Next: results page (evidence/R-0012-stage3-medium-results.html) and progress page update. Founder decides: stage 4
  (own mixed isiXhosa + English recordings, which also targets the main remaining weakness: English loanwords and
  names) or stage 5 (publish R-0012). Remaining stage 3 ideas: real <|xh|> tag, more FLEURS weight, Meta MMS comparison.

## 2026-10-17 22:50 — Talking to the model: Thetha, the live page (D-0014, R-0013)
- Agent/session: Claude Code (isiXhosa Speech AI session, account2)
- Did: built a local listening page (evidence/make_listen.py -> data/listen/listen-R-0012.html, the 20 NCHLT clips with
  four models' outputs and verdict buttons; stays local, contains NCHLT audio). Founder asked to speak to the model and
  for an API; chose laptop now, Hugging Face later (D-0014). Built src/live.py (local HTTP API: /transcribe, /correct,
  /models, /corrections.tsv; 127.0.0.1 only) and src/live.html ("Thetha": record button with a voice-reactive ring,
  self-typing transcripts, click-to-correct, compare medium vs small, hold-to-talk, audio-file drop, copy, export).
  Downloaded models/R-0012 and R-0007 to data/models/; local .venv with CPU torch. Server was stopped once for low
  memory (P-0011). Speed work: shortening the 30 s window broke output (P-0012); CTranslate2 int8 kept accuracy.
- Result: **R-0013: int8 CPU CER 5.67 / WER 31.74 vs GPU fp16 5.69 / 31.06 on 200 unseen-sentence clips; 186/200
  identical.** Live page speed: medium int8 ~3.9 s, small int8 ~1.4 s per recording (fp32 medium was ~11 s).
  The founder and a friend tested it; 12 corrections saved so far in data/my_voice/live/ (local only).
- Cost: $0 (laptop); S3 download of 4 GB of models.
- Open: a friend's consent for keeping their recordings (asked, no answer yet); DirectML (Radeon iGPU) test pending
  (.venv-dml installed); founder's listening-page verdicts.
- Next: stage 4 plan (founder's own mixed isiXhosa + English recordings), or stage 5 (Hugging Face).

## 2026-10-19 11:30 — Stage 4 without recordings: Soapies test set, R-0014, R-0015/R-0016 prepared
- Agent/session: Claude Code (isiXhosa Speech AI session, account3)
- Did: founder is too busy to record; asked for a zero-effort way. Found two SADiLaR datasets that download without a
  login: the Soapies code-switched soap-opera corpus (English-isiXhosa set 3.1 h, research only) and NCHLT English
  (56 h, CC BY 3.0). Founder chose **A: Soapies for testing only, published models trained on open data only (D-0016)**.
  Added both to the cloud downloader (fetch-2, t3.small, MD5s match SADiLaR); in S3 under datasets/soapies_engxho/
  and datasets/nchlt_eng/. Wrote src/soapies.py, src/eval_soapies.py; R-0014 scored our models on the Soapies test.
  Extended src/train.py (English clips with <|en|>, stitched isiXhosa+English clips, Soapies dev for checkpoint choice,
  32 kHz resampling) and wrote runs/R-0015/job.sh (R-0015 + R-0016 on one node), D-0017, docs/stage4.png.
- Result: **R-0014: R-0012 on real mixed speech CER 38.43 / WER 79.59** (R-0007 42.13 / 87.97); English words right
  32 %, isiXhosa 15 %. It spells English the isiXhosa way inside sentences, yet writes whole English phrases perfectly
  (NCHLT isiXhosa contains 534 English-prompt clips). Problem P-0013: two laptop jobs stopped for low memory (stock
  medium on Soapies at 100/391; training smoke test before step 1).
- Cost: ~$0.05 (download node); laptop $0. Project total ~ $9.90.
- Next: re-run stock medium on Soapies and the training smoke test, one at a time; launch R-0015/R-0016 after the
  1 November brake reset with the founder's OK on ~$5-6.

## 2026-10-19 — Project stopped (D-0018)
- Founder decided not to continue. No AWS machines running. Nothing launched or scheduled.
- Left in S3 (bucket mgaguli-studio-render-<acct>): datasets/ 16.4 GB (NCHLT xho + eng, FLEURS, Soapies), models/ 5.0 GB
  (R-0004, R-0007, R-0012), jobs/ 61 GB (run outputs and checkpoints; jobs/ expires automatically after 30 days).
  Roughly $1.90 per month now, ~$0.50 per month once jobs/ expires, until deleted.
- Left on the laptop (gitignored): data/ (models incl. int8 copies, Soapies, NCHLT test audio, Thetha recordings in
  data/my_voice/live/ incl. a friend's clips), .venv. Thetha still works locally.
- Project total spend ~ $9.90.
- Backup: founder asked for a repo; created **private** GitHub repo https://github.com/2Ntlaks/isixhosa-speech-ai and
  pushed the full history (173 files; no audio, models, keys or tokens). Before it could ever be made public: remove the
  AWS account number (6 run files) and the Soapies transcripts quoted in runs/R-0014/ (research-only licence, D-0016).

## 2026-10-19 afternoon — Open-sourcing (D-0019)
- Agent/session: Claude Code (isiXhosa Speech AI session, account3)
- Did: README redesigned (banner, before/after examples, progress chart, pipeline drawing) and MIT licence added.
  Cleaned the repo for publication: AWS account number -> <acct>, a friend's name removed, R-0014 Soapies transcripts
  untracked (kept locally, gitignored), Soapies sentence examples cut to single words. Rewrote history in a copy with
  git-filter-repo (verified: 0 hits for account number, name, quotes, transcript files in all 40 commits; final tree
  identical). Private repo renamed 2Ntlaks/isixhosa-speech-ai-archive; full backup bundle in data/backup/. Public repo:
  https://github.com/2Ntlaks/isixhosa-speech-ai (topics added). Local folder now follows the public history
  (remote "archive" = private).
- Release kit: public mode for Thetha (src/live.py --public: nothing stored; tested on the laptop: correct transcript,
  /correct and /corrections.tsv refused, 0 new files), model cards (CC BY 4.0), Hugging Face Space files (Docker, free
  CPU), release/publish.py (dry run passes; ~5 GB to upload), CITATION.cff, LinkedIn and blog drafts.
- Cost: $0.
- Next: founder creates a Hugging Face account and logs in (`hf auth login`); agent runs release/publish.py, checks the
  Space build, then fills the Hugging Face links into README and the drafts.

## 2026-10-19 evening — Published on Hugging Face; free in-browser demo (D-0020, R-0017)
- Agent/session: Claude Code (isiXhosa Speech AI session, account3)
- Did: founder created a Hugging Face account and logged in himself. Uploaded Ntlakanipho/whisper-medium-isixhosa
  (R-0012, 3.84 GB) and Ntlakanipho/whisper-small-isixhosa (R-0007, 1.22 GB), public, CC BY 4.0, honest model cards.
  The Docker demo was refused: free Docker Spaces need PRO (P-0014). Founder chose a free static demo that runs the
  model in the visitor's browser (D-0020). Converted R-0007 to ONNX 8-bit (two export problems, P-0015), measured it
  (R-0017: CER 6.63 vs 6.43, passed), built release/web (Thetha look, model in a worker, nothing uploaded), tested it in
  headless Chrome locally and live, published https://ntlakanipho-thetha.static.hf.space. README, model cards and
  announcement drafts link to it.
- Cost: $0 (Hugging Face free tier; laptop).
- Next: founder tries the demo on his phone, edits and posts the LinkedIn/blog drafts (release/announce/).
- 2026-10-19: founder confirmed the live demo works on his own device ("it works"), which covers the one path the agent
  could not test (recording from a real microphone).

## 2026-10-19 late — Announcement video (D-0021)
- Agent/session: Claude Code (isiXhosa Speech AI session, account3)
- Did: Remotion film, ~40 s, 7 scenes (hook; stock Whisper looping "kwa kwa kwa"; R-0012 writing the same clip
  exactly; stock vs R-0012 side by side; 65.5 % -> 8.0 % counter; Thetha on a phone; end card with link and credits).
  Voices from three FLEURS test clips (CC BY 4.0); all transcripts are real run outputs (R-0006, R-0011, R-0012).
  Rendered release/video/out/thetha-vertical.mp4 (1080x1920) and thetha-wide.mp4 (1920x1080), 40 s, ~27 MB each,
  h264 + aac. Checked: soundtrack peaks 0.64 (no clipping), voices in the right scenes, frames from the final files.
- Cost: $0 (laptop). MP4s are not in git (size); they are in release/video/out/.
- Video cut 2 (D-0022), after the founder found cut 1 not eye-catching: kinetic launch trailer on a 100 BPM grid with a
  synthesised score. 43.2 s, release/video/out/thetha-vertical.mp4 and thetha-wide.mp4 (~37 MB each). Checked frames
  from the final files and the soundtrack (peak 0.65; deliberate near-silence at ~12 s before the riser and reveal).
- TikTok cut (src/TikTok.tsx): 19.2 s, hook in the first second ("I asked AI to write down isiXhosa…" over the real
  "kwa kwa kwa" loop), "so I trained my own.", same voice resolving into R-0012's exact transcript, three stat punches,
  phone + "link in bio". All text inside TikTok's UI-free zone. Two files: with the synthesised beat, and voices only
  (for a trending sound added in the app). release/video/out/thetha-tiktok*.mp4, ~17 MB each.
