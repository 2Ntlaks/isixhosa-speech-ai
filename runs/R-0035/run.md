# R-0035 · whisper-medium retrained on R-0029's data with the fixed recipe

Before the run (drafted by the builder 2026-11-19; the lead fills in the outcome). Plan: D-0031, step 3.

- **Why:** every medium run stopped at 4000 steps even as the data grew six-fold, so R-0029 saw its 309.7 h only
  1.3 times while its dev loss was still falling; the best checkpoint was picked on NCHLT read speech only; no
  SpecAugment; and the dev evaluations cut sentences off at 96 tokens. This run repeats R-0029's data with those four
  things fixed (Neon's review, step 3; settings from Neon's pre-flight memo, checked by the lead).
- **Not a one-change run:** four recipe changes at once (length, checkpoint choice, SpecAugment, dev generation
  length). If it ships, we will know the recipe helps, not which part. Splitting them is later work if needed.
- **Data (exactly R-0029's):** NCHLT train minus the same 6 dev speakers, FLEURS train <= 30 s, Swivuriso train 1-30 s
  without [?] plus the 20,563 long-clip pieces (98.9 h), with every test and dev sentence (NCHLT test and dev, FLEURS
  dev and test, Swivuriso dev and dev_test) dropped from training. Expected in data_split.json: 98,663 training clips,
  309.68 h, Swivuriso 52,960 clips, 6,139 dropped as test/dev sentences (R-0029's numbers).
- **Model:** `openai/whisper-medium` at revision `abdf7c39ab9d0397620ccaea8974cc764cd0953e` (pinned; R-0029 used the
  same model unpinned), language tag sw (D-0007).
- **Recipe (src/train.py flags; every new option is off by default, and with default flags the new train.py gives
  bit-identical weights and logs to the old one, checked on the laptop):**
  - 9000 steps x 32 clips (8 x 4, falls back to 4 x 8 if the memory check fails) = ~2.9 passes over the data (R-0029:
    4000 steps, 1.3); lr 1e-5, warm-up 500, linear decay (kept linear so only the length changes in the schedule).
  - Evaluation and checkpoint every 1000 steps; 3 checkpoints kept (also mirrored to S3 jobs/R-0035/checkpoints/).
  - **Best checkpoint on `combined_cer` = 0.5 x Swivuriso dev CER + 0.5 x FLEURS dev CER.** Swivuriso dev: 22 clips
    from each of the 24 dev speakers (about half unscripted where a speaker has them), references of at most 220
    tokens, seeded (about 528 clips). FLEURS dev: all 441 clips <= 30 s. NCHLT dev (the same 600 clips as R-0019 and
    R-0029) is scored for information only. Neither dev set is ever trained on (separate speakers and splits).
  - Dev generation length 225 tokens (the old job files passed 96, which cut long dev sentences off).
  - Runaway outputs counted per dev set at every evaluation (> 2.5x the reference and > 150 letters).
  - **SpecAugment:** time masks (probability 0.05, 10 frames = 0.1 s, at least 2), frequency masks (probability 0.10,
    8 of the 80 mel bands, at least 1); training only. The attention mask is passed with every training clip, so time
    masks fall on speech: without it, 89 % of masked frames landed on the silence that pads clips to 30 s (laptop
    check, whisper-tiny). Not done: noise and speed perturbation (Neon's (d)); a later run.
- **Preflight on the node, before any long work (P-0006, P-0007, P-0008 lessons):** (1) the full training data
  split, computed without training (`train.py --split-only`), must equal R-0029's data_split.json (clips, hours,
  speakers, dev speakers, Swivuriso kept and dropped), or the job stops; (2) `src/check_specaug.py` with
  whisper-medium: the mask reaches the model, masks stay inside the audio in training, none in evaluation; (3) the full
  recipe with every flag above on the 16 longest transcripts at batch 8 x 4 for 2 steps, with all three dev sets,
  the combined score, the runaway counts and a save; if it fails, the same at 4 x 8; (4) the int8 copy with its
  processor files and tokenizer.json (P-0020) and the guarded evaluator on the GPU on 3 clips per test set, plus the
  int8 copy on the CPU on 1 clip. Each preflight's full output is kept in out/; a failure prints its last 40 lines.
  Training progress reaches the log every 25 steps (~40 s); the evaluations print a progress line every minute.
- **After training:** the training records (log_history, data_split, train.log) to S3 first, then the best
  checkpoint to S3 models/R-0035/, and only then the COMPLETE marker (F-09). Then, in this order: (1) the four test
  sets with the standard decoding (R-0033: loop guard, beam 5, CTranslate2 float16, GPU), side by side; (2) the old
  evaluator (transformers greedy, src/baseline.py) on NCHLT, FLEURS and Swivuriso, for continuity with results.md;
  (3) the int8 copy to models/R-0035-int8/ (+ COMPLETE). No beam-1 arm (the lead's decision on Neon's F-13: R-0033
  already shows what the guard alone does).
- **Resuming:** if the 6 h cap stops the node, relaunching the same command continues: from the last checkpoint in
  S3 if training was not finished, otherwise straight to the evaluations still missing (finished test sets are
  skipped). Checkpoints are mirrored every 5 min, each complete one with trainer_state.json uploaded last; older S3
  checkpoints are deleted only after every newer local one is confirmed in S3 (F-09).
- **Second home (P-0021 lesson):** S3 is the only copy of the new model until the lead copies it elsewhere (a private
  Hugging Face repo or the laptop). Do that before anything else once the run is done.

## Ship rule (set before the run)
Under the SAME decoding (loop guard, beam 5, CTranslate2 float16 on the GPU, settings of R-0033), R-0035 must:
1. have a **lower Swivuriso test CER** than R-0019 (R-0033's beam-5 number), and
2. have a **lower FLEURS test CER** than R-0019 (R-0033's beam-5 number), and
3. have an **NCHLT test CER at most 0.5 above** R-0019's (R-0033's beam-5 number).
"Lower" means lower at the two decimals the evaluator reports; a tie fails. All three or it does not ship. Its data
split must match R-0029's (numbers above), or the run is not interpreted. Reported but not part of the rule: Soapies,
the old greedy evaluator, unscripted vs scripted, runaways, fallbacks. If it ships: the int8 copy is
checked as R-0020 (CER at most 0.3 above the GPU on the same clips), then it becomes Thetha's default and, with the
founder's OK, the published medium model.

## Command
```
DISK_GB=300 FALLBACK_TYPES="g6e.2xlarge" cloud/run_job.sh --run R-0035 --type g6e.xlarge --market ondemand --max-hours 6
cloud/wait.sh R-0035 && cloud/collect.sh R-0035
```
Launch only after R-0033 (its R-0019 numbers are the bar) and after Neon's review of this code.

## Time and cost estimate (from measured runs)
- **Training steps:** R-0019 on this node type (g6e.xlarge): 7,402 s for 4000 steps with 8 evaluations of ~107 s each
  -> 1.64 s per step (checkpoint saves included). R-0029 on g6e.2xlarge: 1.57 s per step. 9000 steps -> **~4.1 h**.
  SpecAugment and the attention mask add only array work (no measurable cost expected).
- **Dev evaluations, per checkpoint:** NCHLT 600 clips ~68 s (measured, unchanged), FLEURS 441 clips at 225 tokens
  ~95-110 s (measured 0.19 s per clip at 96 tokens), Swivuriso ~528 clips ~50-60 s (0.095 s per clip measured on the
  test set). ~3.5-4 min x 9 = **~35 min**, about 13 % of training time.
- **Before training:** boot and installs ~10 min, data ~15-20 min (36.7 GB of Swivuriso from S3; FLEURS from Hugging
  Face once, then saved back to S3), preflight ~10 min.
- **After training:** uploads and the fp16 conversion ~5 min; standard decoding on four sets side by side ~25 min
  (L40S); old evaluator ~8 min (measured 7.2 min in October); int8 copy ~3 min. ~40 min in all (beam-1 arm dropped).
- **Total ~5.7-6.0 h** against the 6 h cap (before: 5.9-6.2 h). At the measured speeds it fits one launch with little
  margin; if the cap stops it, what is lost is the end (the int8 copy, maybe part of the old evaluator), and a
  relaunch finishes it in ~30 min (~$1). **Cost: ~$10.60-11.20 on g6e.xlarge ($1.861/h), ~$12 with a relaunch;
  ~$13 if only g6e.2xlarge ($2.24/h, 1.57 s per step) is free.** Together with R-0033 and R-0034 (~$2.30-2.90):
  about $13-15, still above D-0031's ~$10-13. The cheapest further cut is 8000 steps (-27 min, ~$0.85); the lead kept
  9000.
- **Checkpoints in S3:** up to 3 x ~9 GB under jobs/ (expires after 30 days), about $0.60 for a month.

## The bar in numbers (filled in from R-0033 before launch, 2026-11-20)
R-0019 under the standard decoding (R-0033 gpu_fp16_beam5): Swivuriso dev_test CER 3.92, FLEURS test CER 5.75, NCHLT
test CER 2.23. R-0035 ships only if Swivuriso < 3.92 AND FLEURS < 5.75 AND NCHLT <= 2.73. R-0034 (Meta Omnilingual
CTC) did not meet its switch rule, so Whisper stays the main path and this run goes ahead (D-0031, D-0032).

## Outcome (lead, 2026-11-20): PASSED the ship rule on all three tests
Attempt 3, i-0675d50370ca38f4e, g6e.2xlarge on-demand, commit daa57a2. Node up 02:35 UTC, DONE 08:02 UTC (~5.5 h,
~$12.25 at $2.24/h). Data split = R-0029's (98,663 clips, 309.68 h, 603 speakers); audio check: all training clips
readable, no dev drops. Training 9000 steps in 4 h 35 min (1.57 s/step), peak GPU memory 34.6 GB at 8 x 4.

**Dev evaluations (combined = 0.5 Swivuriso dev CER + 0.5 FLEURS dev CER; runaways 0 at every step):**

| Step | FLEURS dev loss | FLEURS dev CER | Swivuriso dev CER | Combined |
|---|---|---|---|---|
| 1000 | 0.514 | 8.23 | 5.98 | 7.105 |
| 2000 | 0.429 | 6.76 | 4.60 | 5.68 |
| 3000 | 0.391 | 6.03 | 3.77 | 4.90 |
| 4000 | 0.382 | 5.89 | 3.66 | 4.775 |
| 5000 | 0.377 | 5.78 | 3.42 | 4.60 |
| 6000 | 0.359 | 5.72 | 3.16 | 4.44 |
| 7000 | 0.367 | 5.52 | 3.55 | 4.535 |
| **8000 (kept)** | 0.366 | 5.52 | 3.00 | **4.26** |
| 9000 | 0.363 | 5.37 | 3.35 | 4.36 |

FLEURS dev loss passed R-0029's final 0.382 at step 5000 and kept falling: the extra length helped (R-0029 stopped at
4000). Best checkpoint: checkpoint-8000. A "missing keys: proj_out.weight" warning when loading it is the tied output
layer (Whisper shares it with the token embeddings); the test scores below show the weights are intact.

**Test sets, standard decoding (R-0033: beam 5 + loop guard, CT2 float16, GPU), vs R-0019 under the same decoding:**

| Test set | R-0035 WER / CER | R-0019 (R-0033) WER / CER | Rule | Result |
|---|---|---|---|---|
| Swivuriso dev_test, 2145 | **15.04 / 3.24** | 18.26 / 3.92 | CER < 3.92 | PASS |
| FLEURS test, 1034 | **26.06 / 5.21** | 28.92 / 5.75 | CER < 5.75 | PASS |
| NCHLT test, 2770 | **11.11 / 1.92** | 13.48 / 2.23 | CER <= 2.73 | PASS |
| Soapies test, 391 (not in rule) | 60.84 / 25.98 | 63.37 / 27.08 | - | better |

Breakdowns (rounded by the evaluator to one decimal):
- Swivuriso scripted 16.3 / 3.5 (R-0019 18.5 / 4.0); **unscripted 13.4 / 2.8 (18.0 / 3.8)**: the biggest gain is on
  spontaneous speech, the speech people actually use.
- NCHLT seen sentences 8.1 / 1.4 (10.6 / 1.8); **unseen 24.4 / 4.1 (26.3 / 4.1)**: on NCHLT sentences never trained
  on, CER did not move; most of the NCHLT gain is on sentences that are also in training. Honest reading: on NCHLT the
  longer training mainly fit the read prompts better; the gains that generalise show on Swivuriso and FLEURS.
- Soapies: isiXhosa words heard 35.2 % (30.3 %), English 52.7 % (53.0 %).
- Loop guard fired on 0 clips in every set; no empty outputs.

**Old evaluator (transformers greedy, src/baseline.py), for continuity with results.md:** NCHLT 11.45 / 1.99 (R-0019
13.67 / 2.31), FLEURS 26.64 / 5.56 (30.32 / 6.24), Swivuriso 15.51 / 3.38 (19.12 / 4.12).

**Not one-change:** four recipe changes at once (length, checkpoint choice, SpecAugment, dev generation length). We know
the recipe helps, not which part.

**Model:** S3 models/R-0035/ (3.84 GB, fp32 + processor) and models/R-0035-int8/. jobs/R-0035/ (checkpoints) expires
after 30 days. Still to do before it becomes Thetha's default: the int8 check as R-0020 (CER at most 0.3 above the GPU
on the same clips), a second copy outside S3 (P-0021), and the founder's OK to publish.
