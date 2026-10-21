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
