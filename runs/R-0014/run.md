# R-0014 · Stage 4 starting point: how do our models handle real isiXhosa + English mixed speech?

- **Why:** stage 4 without the founder recording (D-0016). Before training anything for mixed speech, measure where we
  stand on real code-switched speech. This becomes the stage 4 yardstick: every later stage 4 model is scored on it.
- **Test set:** Soapies English-isiXhosa balanced corpus, official test split (`engxho_tst_set_utterance_ids.txt`):
  391 utterances, 14.3 min, 5 speakers (soap-opera characters), 390 of 391 utterances switch language.
  Stellenbosch University, van der Westhuizen & Niesler (LREC 2018), SADiLaR handle 20.500.12185/545, research only:
  scoring only, never training (D-0016). Transcript conventions handled in src/soapies.py ("!" = apostrophe,
  "_" = word broken at a language switch -> split form, as FLEURS hyphens, D-0010).
- **Models (all CTranslate2 int8 on the laptop CPU, same engine as R-0013):**
  1. stock whisper-medium, language auto-detected per clip (the "before" picture; stock Whisper already knows English)
  2. R-0007 (whisper-small, NCHLT + FLEURS), <|sw|> prompt
  3. R-0012 (whisper-medium, NCHLT + FLEURS, best model), <|sw|> prompt
- **Command (per model):** `CT2_USE_MKL=0 .venv/Scripts/python src/eval_soapies.py --model data/models/<model> --lang <sw|auto> --out runs/R-0014/<name>`
- **Scores:** WER, CER (normalisation v1), plus diagnostics: CER without spaces (forgives i grapefruit vs igrapefruit),
  and English / isiXhosa word hits (share of each language's reference words found in the output).
- **Expectation (written before the run):** R-0012 best overall but weak on the English parts (it was only ever trained on
  isiXhosa text, so it may spell English words the isiXhosa way); stock medium good on English words, poor on isiXhosa.
- **Machine:** founder's laptop, $0. Audio pulled from the private S3 bucket (datasets/soapies_engxho/) to data/ (gitignored).

## Outcome · 2026-10-19 · PARTLY DONE (laptop, $0)
| model | WER | CER | CER, spaces ignored | English words right | isiXhosa words right | exact clips | s/clip |
|---|---|---|---|---|---|---|---|
| R-0007 (small) | 87.97 | 42.13 | 39.86 | 17.2 % | 11.5 % | 1/391 | 1.83 |
| **R-0012 (medium)** | **79.59** | **38.43** | 36.44 | 31.8 % | 14.6 % | 3/391 | 4.55 |
| stock medium, auto language | - | - | - | - | - | - | stopped at 100/391 (P-0013) |

- Real mixed speech is much harder than read speech: R-0012 CER 38.4 here vs 8.0 on FLEURS and 2.3 on NCHLT.
  Expectation (R-0012 best) held. Ignoring spaces changes little (36.4), so word-splitting is not the main problem.
- What goes wrong (runs/R-0014/samples.md, kept out of the public repo: research-only transcripts, D-0019): English
  words inside isiXhosa sentences are written with isiXhosa spelling ("stubborn" -> "istabhunga", "biological" ->
  "ngephological"); fast, acted conversational isiXhosa with background sound is also often wrong (only 15 % of
  isiXhosa words right). Once it drifted into French. Some reference transcripts are themselves rough.
- Side finding: NCHLT isiXhosa contains English prompts read by isiXhosa speakers (534 training clips, 0.49 h; 36 test
  clips, 29 of them seen in training). R-0012 writes those perfectly (CER 1.6). So it can write English; it fails when
  English sits inside natural isiXhosa speech. That points at stitched clips (R-0016) more than pure English (R-0015).
- Per test speaker CER (R-0012): SANDRA 32.5, PATRICIA 31.3, MOTHA 39.3, ANDILE 39.3, ZOTHILE 42.7.
- Stock medium: to be re-run alone when the laptop is free (P-0013).
