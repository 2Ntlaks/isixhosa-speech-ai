# R-0022 · Five-candidate audit: is the right word among beam 5's guesses? (laptop, R-0019-int8)

- **Why:** step 1 of the combined plan (docs/combined-plan-2026-10-21.md, Codex's design). A "pick another word" button
  in Thetha, and Claude's word-list rescoring, only help if the right word is already among the 5 beam candidates.
- **One change vs the live page:** `num_hypotheses` 1 -> 5. Same model (R-0019-int8), beam 5, token limit 96, no prompt.
- **Clips (frozen before any output was seen):** `clips.jsonl`: 100 NCHLT clips from the 6 dev speakers held out of
  R-0019's training (005, 023, 066, 077, 173, 192): all 82 whose sentence no training speaker says, plus 18 others
  (seed 1). The NCHLT and FLEURS test sets stay reserved for confirmation. Audio fetched from S3 (8.6 min, gitignored).
  Founder clips: none yet (waiting for his ~20 recordings); they get their own run.
- **Command:** `CT2_USE_MKL=0 .venv/Scripts/python src/decode_audit.py candidates --clips runs/R-0022/clips.jsonl --out runs/R-0022`
- **Git commit at launch:** 2dff2ea (+ src/decode_audit.py, committed with this file). **Machine:** founder's laptop, $0.
- **Pass rule (set before the run):** best-of-5 ceiling WER at least 3 points below the top choice; top choice not worse
  than returning 1 transcript; time at most 1.25x. The ceiling picks the best candidate WITH the reference, so it is an
  upper bound on what a human picking from a list could reach, not an accuracy.
- **If it passes:** build "pick another word" in Thetha and try word-list rescoring. **If not:** drop both; the fix is training.

## Outcome · 2026-10-21 21:00 SAST · PASSED (laptop, $0)
- **Top choice = what Thetha shows today:** WER 30.38 / CER 4.43 on the 100 clips (82 unseen sentences: 34.29 / 4.67).
  Returning 5 candidates changed nothing about the top choice (100/100 identical).
- **Best of 5, picked with the reference (a ceiling, not an accuracy):** WER 18.09 / CER 2.69, i.e. **12.3 WER points**
  below the top choice (pass mark 3). Unseen sentences: 20.82 / 3.02 (-13.5).
- 61 of 100 clips have at least one wrong word in the top choice; in **18 of those, one of the other 4 candidates is
  exactly right**. Of the 83 reference words missing from the top choice, **36 (43 %) appear in another candidate**.
- **Time:** 498.6 s returning 5 vs 496.5 s returning 1 (ratio 1.004): free. Measured while Codex's thread profiler
  shared the CPU, so absolute seconds are noisy; both settings ran interleaved on every clip, so the ratio is fair.
- **Reading:** the right word is often already among the guesses, so a "pick another word" list in Thetha would let a
  person fix about 4 in 10 wrong words with one tap, and an isiXhosa word list could try to pick automatically.
  Caveat: NCHLT dev is short read speech; confirm on the founder's own recordings when he has made them.
