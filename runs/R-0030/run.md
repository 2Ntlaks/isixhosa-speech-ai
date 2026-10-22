# R-0030 · Mixed isiXhosa-English speech (Soapies test): do the Swivuriso models handle code-switching better?

- **Why:** the founder's caption says AI struggles with isiXhosa "especially when we mix it with English". The last
  code-switching score is R-0014 (R-0012 medium: CER 38.4 / WER 79.6; R-0007 small: 42.13 / 87.97). Neither Swivuriso
  model (R-0019 medium, R-0027 small) has been measured on mixed speech.
- **What:** `src/eval_soapies.py` exactly as in R-0014 (391 Soapies test clips, research-only, test only (D-0016); --lang
  sw; greedy; 96-token limit) on R-0019-int8 and R-0027-int8. R-0029-int8 is added when it exists.
- **Commands:** `CT2_USE_MKL=0 .venv/Scripts/python src/eval_soapies.py --model data/models/<model> --lang sw --out runs/R-0030/<run>`
- **Machine:** laptop, $0. Transcripts and outputs stay local (gitignored); only scores go in git.
