# AGENTS.md — isiXhosa Speech AI

Context for any coding agent working in this folder. Read this first. The full human-readable spec is `SPEC.html`.

## What this is

A **learning project** by Ntlakanipho Mgaguli (final-year Computer Engineering, CPUT Bellville): fine-tune
OpenAI Whisper so it can transcribe **isiXhosa**, which Whisper does not support, then specialise it for
isiXhosa–English code-switched speech (stage 4). Goal: learn speech AI deeply, not just ship a model.

**Roles (the founder's explicit choice):** the founder does **not** write code. Coding agents (his Claude Code
sessions) write, test, validate and operate everything: code, data pipelines, training, evaluation, AWS, SSH or
SSM into GPU nodes, Hugging Face publishing. The founder is the **architect and decision-maker**: he must
understand what is happening, why, and how the parts fit, well enough to direct the work and diagnose problems.

What that means for agents:
- **Explain before and after.** Before a stage, a one-page drawing of the architecture or concept in `docs/`
  (hand-drawn style, his brand palette). After a stage, a short plain-language explainer: what ran, what the
  numbers mean, what went wrong and why. Diagrams over walls of text.
- **Surface decisions, don't bury them.** Real choices (model size, data mix, spend) go to the founder with a
  recommendation, and get logged in `decisions.md` (date, choice, why).
- **Make problems visible.** When something fails, explain the cause in terms he can reason about, not just "fixed".
- **Keep state in files, not chat.** Several agent sessions work on this project; the evidence files below are
  how one session hands over to the next.
- **Test and validate your own work** (run it, check outputs, sanity-check numbers) before reporting it done.

## Plan (see SPEC.html §3 and docs/roadmap.png)

1. Baseline: stock `whisper-small` on NCHLT test clips, report WER and CER. Laptop only.
2. First fine-tune of `whisper-small` on NCHLT on one AWS L4 GPU, checkpoints in S3.
3. Improve: text normalisation, add FLEURS `xh_za`, augmentation, larger model, compare with Meta MMS. Keep a results table.
4. Niche: founder's own recordings of mixed isiXhosa + English; held-out test set.
5. Ship: Hugging Face model card (honest scores, data, licence, limits), free demo page, write-up on ntlaks.dev.

## Data and licences

- NCHLT isiXhosa Speech Corpus (SADiLaR, ~56 h, CC BY 3.0): the founder downloads it himself after accepting the
  licence. Credit CSIR Meraka Institute and North-West University. Never re-upload the raw audio.
- Google FLEURS `xh_za`; Mozilla Common Voice isiXhosa is tiny (must not be re-hosted; never identify speakers).
- Data lives in `data/` (gitignored). Never commit audio, checkpoints or tokens.

## AWS

Reuse the guarded setup from `../Mgaguli SA Studio/cloud/` (bucket, IAM role, budgets): one GPU node, hard
`--max-hours` cap, self-terminating, `mgaguli-gpu-monthly` $20 brake and the $20 account alert stay on.
Budget for the whole project: about $15–30 of credits. Confirm credit coverage before using services beyond EC2/S3.

## Conventions

- Report both WER and CER (isiXhosa words are long; one wrong syllable fails the whole word).
- Change one thing per experiment; log every run in `results.md` (date, model, data, steps, WER, CER, cost).
- Honest results only: fixed held-out test speakers, no cherry-picking.
- Never invent isiXhosa text; transcripts come from the datasets or from the founder.

## Source of truth and evidence (mandatory)

The project files are the source of truth, not chat history. They are also the evidence for the final write-up,
so **record as you go, including failures**. Every session:

| File | When to write | What |
|---|---|---|
| `JOURNAL.md` | end of every working session | what was done, results (with run/problem IDs), $ spent, next step |
| `runs/R-xxxx/` | **before** a run starts, completed after | command, git commit, config, logs, metrics, sample outputs, loss curve (see `runs/README.md`) |
| `results.md` | after every run, even failed ones | one table row per run: model, data, test set, WER, CER, GPU hours, cost |
| `problems.md` | whenever something breaks or surprises | exact error text, cause, fix, time/$ lost, one-line lesson |
| `decisions.md` | whenever the founder makes a real choice | options, recommendation, decision, his reason |
| `evidence/` | when there is something to show | screenshots, charts, demo captures, AWS cost screenshots |

Rules: append-only (never rewrite history; add a correction entry instead). IDs are sequential (`R-0001`,
`P-0001`, `D-0001`). Copy exact error messages. Every number in the write-up must cite a run ID. Commit to git
after each session so the history itself is timestamped evidence. Big files (audio, checkpoints, logs > 5 MB)
go to S3, with the path recorded in the run folder.

## Remote access

Prefer AWS SSM Session Manager over opening SSH ports. If SSH is needed, key-based only, restricted to the
founder's IP, and the instance still self-terminates under its time cap. Never commit keys or tokens.

## Status

- 2026-10-16: folder, spec and evidence system created (details in JOURNAL.md). Waiting on the founder: does he speak isiXhosa, SADiLaR account, Hugging Face account.
- 2026-10-16: founder speaks isiXhosa (D-0003). Still waiting on: SADiLaR account + NCHLT download, Hugging Face account.
- 2026-10-16: NCHLT + FLEURS xh_za are in S3 under datasets/ (no SADiLaR account needed, D-0005). Next: stage 1 baseline. Hugging Face account needed only for stage 5.
- 2026-10-16: stage 1 done in the cloud (D-0006): R-0001 baseline WER 196.6 %, CER 75.1 %. Waiting on the founder's listening notes; next is stage 2 (first fine-tune). Fix P-0002 (SSM) first.
- 2026-10-17: stage 2 done: R-0004 (whisper-small, 4000 steps, <|sw|> tag) test CER 2.98 % / WER 16.63 %; unseen sentences CER 6.2 % / WER 36.6 %. Model in S3 models/R-0004/. Next: stage 3 experiments (see JOURNAL).
- 2026-10-17: stage 3 exp 1 done: R-0007 (whisper-small, NCHLT+FLEURS) is the best model: FLEURS test CER 10.16 / WER 44.38 (R-0004: 29.81 / 94.86), NCHLT test CER 2.91 / WER 16.80. Model in S3 models/R-0007/.
- 2026-10-17: stage 3 exp 2 done: R-0012 (whisper-medium, NCHLT+FLEURS) is the best model: FLEURS test CER 8.03 / WER 37.83, NCHLT test CER 2.33 / WER 12.71 (unseen 5.0 / 28.7). Model in S3 models/R-0012/ (3 GB). October GPU brake near $17 of $20.
- 2026-10-17: Thetha live page on the laptop (src/live.py, D-0014): R-0012/R-0007 as CTranslate2 int8 in data/models/ (R-0013: same accuracy as GPU). Founder corrections collect in data/my_voice/live/ (stage 4 material). Next: stage 4 plan.
- 2026-10-17 (end of day): **next session starts from TODO.md** (stage 4 niche + deploying: private GitHub repo, Hugging Face). Thetha restart: `$env:CT2_USE_MKL="0"; .venv\Scripts\python src\live.py`. No AWS machines running.
- 2026-10-19: stage 4 without founder recordings (D-0016): Soapies code-switched TV speech = test/dev only, training on open data (NCHLT + FLEURS + NCHLT English). R-0014: R-0012 on Soapies test CER 38.4 / WER 79.6. R-0015/R-0016 (English, stitched clips) ready in runs/R-0015/job.sh; launch after 1 Nov with founder OK. Laptop: one heavy job at a time (P-0013).
- 2026-10-19: **project stopped by the founder (D-0018).** Do not launch runs. Leftover S3/laptop data listed in JOURNAL; delete only on his word.
- 2026-10-19 (end of day): **published.** Code public (github.com/2Ntlaks/isixhosa-speech-ai), models on Hugging Face (Ntlakanipho/whisper-medium-isixhosa, whisper-small-isixhosa), free in-browser demo (ntlakanipho-thetha.static.hf.space), blog post live (ntlaks.dev/writing/teaching-whisper-isixhosa/), launch/TikTok videos in release/video/out/. S3 holds only models/ (~$0.12/month after jobs/ expires ~16 Nov). Open: friend's voice clips in data/my_voice/live/ (consent unconfirmed), stage 4 (R-0015/R-0016) waits for the founder.
