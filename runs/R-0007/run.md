# R-0007 · Stage 3, experiment 1: add FLEURS to the training data

- **Why:** R-0004 plateaued from step 3000 and is much weaker on sentences it never practised (6.2 % vs 2.2 % CER).
  More varied data (long natural sentences, different speakers and recording conditions) should help with exactly that.
- **One change vs R-0004:** training data = NCHLT + FLEURS train (~13 h). Everything else identical, including dev speakers.
- **Command:** `cloud/run_job.sh --run R-0007 --max-hours 4 --market ondemand` (the node also runs R-0005 and R-0006 first).
- **Founder approval:** 2026-10-17, "yes do what you have to do" (~$2.20).
- **Expected:** clearly better on FLEURS test than R-0005; NCHLT test about the same as R-0004 (it must not get worse).
- **Reviewed before launch** by a separate reviewer agent (2026-10-17). It downloaded the real FLEURS/NCHLT text and
  checked parsing, comparability, label lengths, pipefail, cost. No crash found. Fixed before launch:
  1. FLEURS "normalised" text still has hyphens (2 901 in train), digits and some punctuation; NCHLT has none. Training
     targets for FLEURS now use scoring.normalise() (hyphen -> space, punctuation removed), the exact form scored (D-0010).
  2. NCHLT generation limit kept at 96 tokens (dev eval and NCHLT test eval) so dev-based checkpoint choice and the NCHLT
     score stay comparable with R-0004; 225 is used for FLEURS evaluations only.
  3. FLEURS drop count recorded in data_split.json; a second preflight trains 2 steps on NCHLT + FLEURS before the long run.
  Noted, not changed (same for every run): 6 FLEURS test references contain [bracketed] words that scoring removes, and
  FLEURS references write numbers as digits (e.g. 10-60) while speakers say them as words, so FLEURS scores have a floor
  that is not the model's fault.

## Outcome
(filled in after the run)
