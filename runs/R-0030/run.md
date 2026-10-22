# R-0030 · Mixed isiXhosa-English speech (Soapies test): do the Swivuriso models handle code-switching better?

- **Why:** the founder's caption says AI struggles with isiXhosa "especially when we mix it with English". The last
  code-switching score is R-0014 (R-0012 medium: CER 38.4 / WER 79.6; R-0007 small: 42.13 / 87.97). Neither Swivuriso
  model (R-0019 medium, R-0027 small) has been measured on mixed speech.
- **What:** `src/eval_soapies.py` exactly as in R-0014 (391 Soapies test clips, research-only, test only (D-0016); --lang
  sw; greedy; 96-token limit) on R-0019-int8 and R-0027-int8. R-0029-int8 is added when it exists.
- **Commands:** `CT2_USE_MKL=0 .venv/Scripts/python src/eval_soapies.py --model data/models/<model> --lang sw --out runs/R-0030/<run>`
- **Machine:** laptop, $0. Transcripts and outputs stay local (gitignored); only scores go in git.

## Outcome · 2026-10-22 (laptop, $0)
| Model | CER % | WER % | English words heard | isiXhosa words heard | s per clip |
|---|---|---|---|---|---|
| R-0007 small, demo before (R-0014) | 42.13 | 87.97 | 17.2 % | 11.5 % | 1.83 |
| **R-0027 small, demo now** | **32.80** | **71.48** | **38.4 %** | **24.6 %** | 1.47 |
| R-0012 medium, before (R-0014) | 38.43 | 79.59 | 31.8 % | 14.6 % | 4.55 |
| **R-0019 medium, now** | **29.29** | **66.62** | **49.3 %** | **27.3 %** | 4.99 |
("words heard": share of the reference words of each language that appear in the output, word order ignored.)
- Both Swivuriso models are clearly better on mixed speech: the demo model's letter errors fell 42.1 -> 32.8 % and it
  now catches 38 % of the English words instead of 17 %. Swivuriso marks English words and keeps them in English
  ([cs] tags), which is the likely reason.
- **Still weak:** about one letter in three is wrong, and two thirds of the words. Soapies is hard (TV drama: fast,
  emotional, background sound), and none of our training data is code-switched TV speech. Mixed speech remains the
  project's hardest test; the caption's "I improved Thetha on this" is supported, "solved" would not be.
