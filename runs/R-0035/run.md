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
- **Preflight on the node, before any long work (P-0006, P-0007, P-0008 lessons):** (1) `src/check_specaug.py` with
  whisper-medium: the mask reaches the model, masks stay inside the audio in training, none in evaluation; (2) the full
  recipe with every flag above on the 16 longest transcripts at batch 8 x 4 for 2 steps, with all three dev sets,
  the combined score, the runaway counts and a save; if it does not fit, the same at 4 x 8; (3) the int8 copy with its
  processor files and tokenizer.json (P-0020) and the guarded evaluator on the GPU on 3 clips per test set, plus the
  int8 copy on the CPU on 1 clip. Training progress reaches the log every 25 steps (~40 s).
- **After training:** the best checkpoint to S3 models/R-0035/ (+ COMPLETE), the int8 copy to models/R-0035-int8/
  (+ COMPLETE). Then, in this order: (1) the four test sets with the standard decoding (R-0033: loop guard, beam 5,
  CTranslate2 float16, GPU); (2) the old evaluator (transformers greedy, src/baseline.py) on NCHLT, FLEURS and
  Swivuriso, for continuity with results.md; (3) the guard with beam 1.
- **Resuming:** if the 6 h cap stops the node, relaunching the same command continues: from the last checkpoint in
  S3 if training was not finished, otherwise straight to the evaluations still missing.
- **Second home (P-0021 lesson):** S3 is the only copy of the new model until the lead copies it elsewhere (a private
  Hugging Face repo or the laptop). Do that before anything else once the run is done.

## Ship rule (set before the run)
Under the SAME decoding (loop guard, beam 5, CTranslate2 float16 on the GPU, settings of R-0033), R-0035 must:
1. have a **lower Swivuriso test CER** than R-0019 (R-0033's beam-5 number), and
2. have a **lower FLEURS test CER** than R-0019 (R-0033's beam-5 number), and
3. have an **NCHLT test CER at most 0.5 above** R-0019's (R-0033's beam-5 number).
"Lower" means lower at the two decimals the evaluator reports; a tie fails. All three or it does not ship. Its data
split must match R-0029's (numbers above), or the run is not interpreted. Reported but not part of the rule: Soapies,
the beam-1 arm, the old greedy evaluator, unscripted vs scripted, runaways, fallbacks. If it ships: the int8 copy is
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
- **After training:** uploads and the two conversions ~10 min; standard decoding on four sets in parallel ~25 min
  (L40S); old evaluator ~8 min (measured 7.2 min in October); beam-1 arm ~12 min.
- **Total ~5.9-6.2 h** against the 6 h cap, so the last evaluations (the old evaluator and beam 1) may be cut off;
  a relaunch then finishes them in ~40 min. **Cost: ~$11-11.5 on g6e.xlarge ($1.861/h) plus ~$1.2 for a relaunch,
  about $12-13; ~$14-15 if only g6e.2xlarge ($2.24/h) is free.** Together with R-0033 and R-0034 (~$2-2.50): about
  $14-17, above D-0031's ~$10-13. Ways to cut it, each with a cost: 8000 steps instead of 9000 (-27 min, ~$0.85),
  dropping the beam-1 arm and the old evaluator for R-0035 (-20 min), NCHLT dev 300 clips instead of 600 (-5 min).
- **Checkpoints in S3:** up to 3 x ~9 GB under jobs/ (expires after 30 days), about $0.60 for a month.
