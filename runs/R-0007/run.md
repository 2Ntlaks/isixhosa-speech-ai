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

## Outcome · 2026-10-17 · DONE (commit 7e6acb3, node i-07a2651bbc20319ef)
- Machine 10:19-12:46 UTC (~2.45 h incl. R-0005 and R-0006, about $1.97 in total; R-0007 itself ~$1.90).
  Training 7 764 s for 4000 steps (1.94 s/step incl. evaluations). Both preflights passed.
- Data: 45 703 training clips, 64.2 h (NCHLT 42 269 + FLEURS 3 434; 32 FLEURS clips over 30 s dropped).
- Dev CER (same 600 NCHLT clips as R-0004): 500: 6.99 · 1000: 5.26 · 1500: 4.48 · 2000: 4.42 · 2500: 3.80 ·
  3000: 3.75 · 3500: 3.83 · 4000: 3.74 (best, kept). R-0004 ended at 3.53. See loss.png.
- **FLEURS test (1034 clips, all unseen sentences): WER 44.38 %, CER 10.16 %** (R-0005, same test, NCHLT-only model:
  WER 94.86, CER 29.81; R-0006 stock + tag: 185.34 / 65.45). Word count now right: 16 708 words written for 16 703.
  Median clip CER 8.75 %; 212 clips under 5 %, 62 clips at 20 % or more. Exact clips only 1.3 % (16-word sentences).
  Clips whose reference has digits (200): CER 12.8 % vs 9.5 % without; 207 outputs contain digits.
- **NCHLT test: WER 16.8 %, CER 2.91 %, 64.4 % exact** (R-0004: 16.63 / 2.98 / 64.51).
  Seen sentences WER 12.7 / CER 2.2 (R-0004 12.1 / 2.2); **unseen WER 34.9 / CER 5.8 (R-0004 36.6 / 6.2)**.
- Conclusion: adding 13 h of FLEURS fixed long-sentence word boundaries (FLEURS WER 95 -> 44) at no cost on NCHLT,
  and slightly improved NCHLT unseen sentences. Dev (NCHLT only) is slightly worse (3.74 vs 3.53), so dev alone would
  have hidden the gain: future runs should also score a FLEURS dev set.
- Model: s3://mgaguli-studio-render-<acct>/models/R-0007/. Comparisons: comparison_fleurs.json, comparison_nchlt.json.
