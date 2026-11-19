# Preflight Research Brief for R-0033, R-0034, and R-0035

Date: 2026-11-19
Author: Research Sub-Agent (for Ntlakanipho Mgaguli, Lead Agent, and Builder Agent)
Scope: Preflight design answers for resuming development under `decisions.md` D-0031: R-0033 (loop-guarded re-score of R-0019 via `faster-whisper`), R-0034 (Meta Omnilingual CTC `300M_v2` and `1B_v2` vs Thetha), and R-0035 (`whisper-medium` retrained on 309.7 h with longer training, Swivuriso + FLEURS checkpoint selection, and SpecAugment).

Label key used on every claim and bullet below:
- `[SOURCE]`: Fact read directly in a primary external source opened during this task (working link in Sections 8 and 9).
- `[REPO]`: Fact read directly in repository files (with file path and run, decision, or problem ID).
- `[INFERENCE]`: Engineering analysis, calculation, or recommendation derived from `[SOURCE]` and `[REPO]` evidence, kept separate from external claims.
- `UNVERIFIED`: Fact that could not be confirmed from an opened primary source (also collected in Section 7).

---

## Plain-English Glossary (Terms Explained Once)

- **WER (Word Error Rate)** and **CER (Character Error Rate):** The percentage of words (WER) or letters (CER) that must be inserted, deleted, or substituted to turn a model's transcript into the reference text. Lower is better.
- **CTC (Connectionist Temporal Classification):** A speech recognition architecture that predicts characters directly for each short audio frame in parallel, without a text-generating decoder that can loop.
- **Greedy decoding vs beam search:** Greedy decoding picks the single highest-probability next token at every step; beam search tracks the top `k` partial transcripts simultaneously (for example `beam_size=5`).
- **Temperature fallback:** Retrying a failed Whisper decode with higher randomness (`temperature > 0`) to escape a stuck repetition loop or low-confidence output.
- **Gzip compression ratio:** The size of text divided by its zlib/gzip-compressed size; repetitive loops compress tightly and produce a high ratio (above 2.4).
- **VAD (Voice Activity Detection):** A lightweight model (such as Silero VAD) that detects where human speech starts and stops so silent stretches are removed before transcription.
- **SpecAugment:** Randomly zeroing rectangular strips of time frames and frequency bands on the log-mel spectrogram (the 2D sound image) during training to reduce overfitting.
- **Epoch:** One full pass over every clip in the training set.
- **Paired comparison and cluster variance:** Comparing two models on the exact same clips removes between-speaker difficulty differences, while speaker clustering means utterances from the same person share correlated errors.

---

## Executive Summary: Short Answers and Recommended Settings

| Question | Recommended Setting / Verdict | Confidence |
|---|---|---|
| **Q1. Test overlap (R-0034)** | Treat **Soapies test** (zero-shot for both) and **FLEURS test** (in-domain train, held-out test for both) as the primary fair head-to-head benchmarks. Flag **Swivuriso `dev_test`** as **high overlap risk** for Meta (report **unscripted** and **scripted** separately; Meta funded African Next Voices, trained on 7,200 h of it, and does not document which splits were used or any cross-split prompt deduplication). Treat full **NCHLT test** as unfair to Meta (Thetha trained on NCHLT and 81.6% of test clips repeat training sentences); compare only **NCHLT unseen sentences (511 clips)** with a domain caveat. | High on FLEURS/Soapies/NCHLT bias; Medium-High on Swivuriso risk (exact Meta split list is `UNVERIFIED`) |
| **Q2. Running Omnilingual CTC v2 fairly (R-0034)** | Use `omnilingual-asr==0.2.0` (Python 3.12 + `libsndfile`) and `ASRInferencePipeline(model_card="omniASR_CTC_300M_v2" or "omniASR_CTC_1B_v2")`. **Do not pass `lang`** (CTC models ignore it; `"xho_Latn"` applies only to LLM variants). Clips must be <= 40 s (recommended <= 30 s); pipeline resamples to 16 kHz mono and normalizes automatically. Because `omniASR_tokenizer_written_v2.model` emits uppercase, 31 ASCII punctuation marks, **curly apostrophes (`U+2019`)**, and digits, keep `src/scoring.py` `v1` as primary but add two fairness diagnostics: normalize curly apostrophes to `'` before `normalise()`, and report a **digit-free FLEURS subset (834 clips)** plus `cer_no_spaces` on Soapies. Prefer a cheap Linux GPU (`g6.xlarge`, < $0.40) over CPU; if running on CPU, benchmark `dtype=torch.float32` vs default `bfloat16` (Issue #57 reports `float32` can be 2-3x faster on CPU). | High |
| **Q3. Loop guards for fine-tuned Whisper (R-0033 and `src/live.py`)** | Use `WhisperModel.transcribe` (never `BatchedInferencePipeline`, which ignores temperature fallback tuples). Always set `language="sw"`, `task="transcribe"`, `without_timestamps=True`, `condition_on_previous_text=False`, `no_speech_threshold=None`, `log_prob_threshold=None`, `compression_ratio_threshold=2.4`, `temperature=(0.0, 0.2, 0.4, 0.6)`, `best_of=5`, `repetition_penalty=1.0`, `no_repeat_ngram_size=0`. For **R-0033 scoring**, set `vad_filter=False` and report two paired columns: **Arm A (`beam_size=1` + loop guard)** and **Arm B (`beam_size=5` + loop guard)** alongside fallback trigger counts. For **`src/live.py`**, use Arm B plus **`vad_filter=True`**. | High |
| **Q4. SpecAugment for HF Whisper (R-0035)** | Set `model.config.apply_spec_augment = True`, `mask_time_prob = 0.05`, `mask_time_length = 10`, `mask_time_min_masks = 2`, **`mask_feature_prob = 0.10`** (or `0.15`; HF default is `0.0`, which leaves frequency masking off), `mask_feature_length = 8`, `mask_feature_min_masks = 1`. **Critical plumbing fix:** enable `return_attention_mask=True` in `WhisperFeatureExtractor` and pass `attention_mask` from `Collator` into `WhisperForConditionalGeneration.forward`, otherwise ~87% of time masks on short clips land on silence padding. | Medium-High (exact code verified; specific `0.10`/`8` tuning on 310 h is `[INFERENCE]`, no direct Whisper-medium 310 h ablation found) |
| **Q5. Training length and schedule (R-0035)** | Train for **`--max-steps 9000`** (**2.92 epochs** on 98,663 clips at effective batch 32; or `8000` steps = 2.59 epochs if targeting strictly under $10 on `g6e.2xlarge`), **`--lr 1e-5`**, **`--warmup 500`**, **`linear` decay** to 0, **`--eval-every 1000`** (or `750`), **`--max-hours 7`**. Estimated total wall time and cost for 9,000 steps + test evals: **~4.8 h (~$8.90 on `g6e.xlarge` at $1.861/h; ~$10.70 on `g6e.2xlarge` at $2.24/h)**. | High |
| **Q6. Checkpoint selection (R-0035)** | Score **480 to 600 Swivuriso `dev` clips stratified across all 24 dev speakers** (20 to 25 clips per speaker, preserving scripted/unscripted mix; ~46-57 s/eval on L40S) AND **all ~440 FLEURS `dev` clips** (not capped at 200; ~85 s/eval on L40S). **Fix a hidden bug:** raise `--generation-max-length` from `96` (used in R-0019/R-0029 `job.sh`) to **`225`** and filter the dev subset to references <= 220 tokens so long dev clips are not truncated. Select best checkpoint via **`eval_combined_cer = 0.5 * eval_swivuriso_cer + 0.5 * eval_fleurs_cer`** (keeping NCHLT dev as info-only) and log runaway clip counts per eval with `save_total_limit=3`. | High |

---

## 1. Question 1: Test Overlap Between Meta Omnilingual ASR and Our Four Test Sets

### 1.1 What primary sources actually say about Meta's training data

- `[SOURCE]` **Omnilingual ASR paper (`arXiv:2511.09690v1`, posted 2025-11-12), Section 3.3.2 ("Partner-Created ASR Data") and Table 3:** Meta explicitly states that it provided funding and resources to the African Next Voices consortium (citing Marivate et al., 2025, Swivuriso). Table 3 ("Summary statistics of the training split of the combined `AllASR` dataset") lists **7,200 hours across 13 languages** from African Next Voices, alongside 15,000 h of open-source datasets (200 languages), 150,100 h of "LTPP [Language Technology Partner Program], internal & licensed data" (1,100 languages), 1,940 h of Open Multilingual Speech Fund (177 languages), 110 h of Lanfrica/Naijavoices (11 languages), and 3,350 h of the commissioned Omnilingual ASR Corpus (348 languages).
- `[SOURCE]` **Internal hour-accounting ambiguity in Omnilingual ASR:** In `arXiv:2511.09690v1` Table 3, the listed rows sum to 177,700 hours while the printed total row says 120,710 hours, and the repository's `per_language_results_table_7B_llm_asr.csv` sums to 196,226.7 hours (independently flagged in `facebookresearch/omnilingual-asr` GitHub Issue #82, still open without an author reply). That CSV reports **`xho_Latn` = 598.8 Training Hours** (and `4.9` CER for the 7B LLM model).
- `[SOURCE]` **What `facebook/omnilingual-asr-corpus` on Hugging Face is:** Direct inspection of `facebook/omnilingual-asr-corpus/raw/main/README.md` confirms that this Hugging Face dataset contains only Meta's 348 commissioned under-served languages (3,350 h total) and **does not include `xho` / isiXhosa at all**. It is not the full `AllASR` training set.
- `[SOURCE]` **Swivuriso paper (`arXiv:2512.02201v3`) and Hugging Face dataset (`dsfsi-anv/za-african-next-voices`):**
  - Section 10 ("Acknowledgements") states: "The project was funded through a grant from the Gates Foundation and a gift from Meta."
  - The Hugging Face dataset metadata (`https://huggingface.co/api/datasets/dsfsi-anv/za-african-next-voices`) shows the repo was created on **2025-07-09** (four months before `arXiv:2511.09690v1` and five months before the Dec 2025 v2 checkpoints).
  - Swivuriso Table 2 reports total `XHO` statistics across the full corpus: **73,665 clips, 485 speakers, 504.28 hours** (average duration 24.64 s).
  - Swivuriso Table 3 and Table 4 report the three publicly released splits (described on the dataset card as speaker-disjoint 85% / 5% / 5%, with 5% held out as a private `test` split):
    - `train`: 62,786 clips, 407 speakers, **427.40 hours** (sum of XHO domain hours in Table 4).
    - `dev`: 3,768 clips, 24 speakers, **25.18 hours**.
    - `dev_test`: 3,639 clips, 24 speakers, **25.60 hours**.
    - Hidden `test` (by subtraction from Table 2): ~3,472 clips, 30 speakers, **~26.10 hours**.
- `[SOURCE]` **Other isiXhosa datasets named in `arXiv:2511.09690v1` Section 3.3.1:**
  - **FLEURS** (Conneau et al., 2023) is explicitly listed as training data in Section 3.3.1, and Section 5.7.2 (Table 18, corpus holdout ablation) explicitly evaluates `AllASR_x_fleurs` against full `AllASR` on FLEURS `dev`, confirming FLEURS `train` is inside `AllASR` training while FLEURS `dev` and `test` are evaluated in Tables 5, 6, and 7.
  - **Common Voice v22** (Ardila et al., 2020) is listed (isiXhosa in Common Voice is tiny).
  - **van Niekerk et al. (2017)** ("Rapid development of TTS corpora for four South African languages", Interspeech 2017) is listed.
  - **MMS-lab** (Pratap et al., 2024; Bible recordings) is included in `AllASR` (Section 5.7.2).
  - **NCHLT** (Barnard et al., 2014 / SADiLaR) and **Soapies** (van der Westhuizen & Niesler, LREC 2018) are **never cited** anywhere in `arXiv:2511.09690v1`.
- `[SOURCE]` **Omnilingual v2 (`omniASR_CTC_300M_v2`, `omniASR_CTC_1B_v2`):** Released in GitHub PR #48/#49 on 2025-12-12 (`README.md`, "December 2025 Update"). Neither the paper (`v1` only, 2025-11-12) nor the GitHub repo documents what training data or splits changed between v1 and v2 (`UNVERIFIED`).

### 1.2 Swivuriso overlap analysis (why `dev_test` is not a clean comparison)

- `[INFERENCE]` **Channel 1: Unknown split boundary and the 598.8-hour gap (`UNVERIFIED`).** Neither `arXiv:2511.09690v1` nor `facebookresearch/omnilingual-asr` states whether Meta trained strictly on Swivuriso's `train` split (427.40 h) or received a pre-split partner delivery or ingested `dev`/`dev_test` as well. Adding up every public isiXhosa training split named in Section 3.3.1 (Swivuriso `train` 427.4 h + FLEURS `train` 13.0 h + van Niekerk 2017 TTS + Common Voice v22 + MMS-lab Bible) leaves roughly 100 to 150 hours below the reported **598.8 hours** for `xho_Latn` in `per_language_results_table_7B_llm_asr.csv`. That extra ~100 to 150 hours could come from Meta's opaque 150,100 h "LTPP, internal & licensed data" bucket (which could also include public South African corpora such as NCHLT), from additional African Next Voices deliveries, or from Swivuriso non-train splits. We cannot prove `dev_test` was excluded.
- `[REPO]` **Channel 2: Confirmed cross-split scripted sentence overlap in Swivuriso.** Even if Meta trained strictly on Swivuriso's official speaker-disjoint `train` split, `runs/R-0019/run.md` and `runs/R-0019/model/data_split.json` prove that **6,139 of 38,536 kept 1-30 s Swivuriso `train` clips (15.9%) carry an exact sentence that also appears in Swivuriso `dev` or `dev_test`** (plus 126 long train clips dropped in `runs/R-0027/run.md`), because Swivuriso's scripted prompts (from Pula/Imvula, Vukuzenzele, Wikipedia, African Wordnet, and goatkeepers manuals; `arXiv:2512.02201v3` Section 3.3.2) were read by multiple speakers across splits. Thetha explicitly removed all 6,139 overlapping sentences via `--exclude-texts` (`src/train.py` lines 220-232). By contrast, `arXiv:2511.09690v1` Section 3.4 describes SAT text splitting, forced alignment, WER filtering, and rare-character filtering, with **no cross-split transcript deduplication**. On the 1,422 scripted clips in Swivuriso `dev_test`, Meta therefore likely saw the exact test sentences during training while Thetha did not.
- `[INFERENCE]` **Why unscripted Swivuriso `dev_test` (723 clips) is cleaner than scripted (1,422 clips), but still caveated:** In Swivuriso's unscripted split (`arXiv:2512.02201v3` Section 3.3.1), speakers answered open-ended questions in their own words, so cross-split verbatim sentence repetition does not occur by design. However, Channel 1 (whether Meta's partner data included any `dev_test` audio/speakers directly) remains `UNVERIFIED`.

### 1.3 FLEURS `xh_za`, NCHLT `xho`, and Soapies `engxho` overlap analysis

- `[SOURCE]` **FLEURS `xh_za` test:** Conneau et al. (`arXiv:2205.12446v1`, Section 2.1) split FLEURS into `train`, `dev`, and `test` with disjoint speakers between `train`/`dev` and `test` and disjoint FLoRes-101 sentences across splits. Both Meta Omnilingual ASR (`arXiv:2511.09690v1` Section 3.3.1, Tables 5-7, Table 18) and Thetha (`runs/R-0019/model/data_split.json`: 3,434 train clips, 13.03 h) trained on FLEURS `train` and evaluated on held-out FLEURS `test`. Could FLEURS `test` leak into Omnilingual? Meta explicitly evaluates its released models on FLEURS `dev` and `test` (Tables 5-7), and `workflows/dataprep/README.md` partitions corpora strictly by `split=train` / `dev` / `test`, making direct FLEURS `test` audio leakage into v1 very unlikely (for v2, exact data changes are `UNVERIFIED`).
- `[REPO]` **NCHLT `xho` test:** Thetha trained directly on NCHLT `train` (51.2 h), and **2,259 of 2,770 NCHLT test clips (81.6%) repeat exact training sentences** (`decisions.md` note 2026-10-17; `runs/R-0027/run.md`). Meanwhile `arXiv:2511.09690v1` never cites NCHLT (though inclusion inside Meta's unitemized 150,100 h internal/LTPP/licensed bucket cannot be ruled out and is `UNVERIFIED`). Full NCHLT test therefore heavily favors Thetha; only the **511 unseen-sentence clips** remove prompt memorization, and even those retain studio-microphone home-ground advantage for Thetha.
- `[REPO]` **Soapies `engxho` test (391 clips, 5 speakers, 14.3 min):** Research-only TV drama code-switched corpus (`decisions.md` D-0016; `src/soapies.py`). Thetha never trained on it, and `arXiv:2511.09690v1` never cites van der Westhuizen & Niesler (2018) or Soapies. Because Soapies carries a "research only" licence (`decisions.md` D-0016), commercial Apache 2.0 training inclusion by Meta is very unlikely (though `UNVERIFIED` against Meta's private licensed/internal list).

### 1.4 Verdict: Which test sets give a fair Thetha vs Meta comparison in R-0034

| Test Set | Thetha Exposure | Meta Omnilingual Exposure | Fair Comparison Verdict |
|---|---|---|---|
| **Soapies `engxho` test (391 clips)** | Zero-shot (never trained on, D-0016) | Not cited; research-only licence makes inclusion very unlikely (`UNVERIFIED` vs internal pool) | **Fairest zero-shot head-to-head** (note small sample: 5 TV speakers, 14.3 min) |
| **FLEURS `xh_za` test (1,034 clips <= 30 s)** | Trained on FLEURS `train`; `test` held out | Trained on FLEURS `train`; `test` held out (v2 changes `UNVERIFIED`) | **Fair held-out-split comparison** (also report 834 digit-free clips per Q2) |
| **Swivuriso `dev_test` unscripted (723 clips)** | Trained on Swivuriso `train` (speakers disjoint; sentences filtered) | Trained on ANV; exact split inclusion `UNVERIFIED`, but open-ended answers avoid scripted-prompt overlap | **Secondary with explicit caveat** (cannot prove Meta excluded `dev_test` clips/speakers) |
| **Swivuriso `dev_test` scripted (1,422 clips)** | Trained on Swivuriso `train` with 6,139 overlapping test/dev sentences removed | Trained on ANV; split inclusion `UNVERIFIED` AND likely trained on repeated scripted prompts | **Not fair as a clean benchmark** (report separately as diagnostic only) |
| **NCHLT `xho` test (2,770 clips)** | Trained on NCHLT `train`; 81.6% of test clips repeat train sentences | Not cited (`UNVERIFIED` vs internal pool) | **Not fair on full set** (heavily favors Thetha). Report **511 unseen-sentence clips** only, with home-ground caveat |

---

## 2. Question 2: Running Omnilingual CTC v2 Fairly

### 2.1 Official inference API, package version, and input requirements

- `[SOURCE]` **Package requirement (`facebookresearch/omnilingual-asr` `pyproject.toml`, Issues #50, #52, #87):**
  - The v2 model cards (`omniASR_CTC_300M_v2`, `omniASR_CTC_1B_v2`) require **`omnilingual-asr==0.2.0`** (v0.1.0 raises `ModelNotKnownError: omniASR_CTC_1B_v2 is not a known model`, Issue #50).
  - `pyproject.toml` specifies `requires-python = ">=3.10,<3.14"` and `fairseq2[arrow]>=0.5.2,<=0.6.0`. Issue #52 notes Python 3.13/3.14 had wheel issues and Python 3.12 worked cleanly. `README.md` notes `libsndfile` is required for audio decoding.
- `[SOURCE]` **Official Python API (`src/omnilingual_asr/models/inference/pipeline.py` lines 148-219, 560-628; `inference/README.md` Section 3.1):**
  ```python
  import torch
  from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline

  pipeline = ASRInferencePipeline(
      model_card="omniASR_CTC_300M_v2",  # or "omniASR_CTC_1B_v2"
      device="cuda",                     # or "cpu"
      dtype=torch.bfloat16,              # use torch.float32 to benchmark on CPU
  )
  transcriptions = pipeline.transcribe(audio_files, batch_size=8)
  ```
- `[SOURCE]` **Language code for isiXhosa:**
  - In `src/omnilingual_asr/models/wav2vec2_llama/lang_ids.py`, the exact code for isiXhosa is **`"xho_Latn"`**.
  - **Crucial for CTC models:** `inference/README.md` Section 3.1 explicitly states that `omniASR_CTC_{300M,1B,3B,7B}_v2` **"don't support language conditioning or context examples."** In `pipeline.py` lines 596-597, passing `lang` to a CTC model logs `Found lang=... with a CTC model. Ignoring.` Only `omniASR_LLM_*` models use `lang=["xho_Latn", ...]`.
- `[SOURCE]` **Input requirements and automatic preprocessing (`pipeline.py` lines 61, 79-145, 414-472; `datasets/utils/audio.py`):**
  - Accepts `List[str | Path]` (file paths), `List[bytes]`, `List[np.ndarray]` (`uint8`/`int8` encoded bytes), or `List[dict]` (`{"waveform": array_or_tensor, "sample_rate": int}`).
  - Internally decodes audio, converts to mono, resamples to **16,000 Hz** via `torchaudio.functional.resample`, and applies per-utterance zero-mean unit-variance `torch.nn.functional.layer_norm` (`audio.py` lines 22-25).
  - **Hard 40-second cap:** `MAX_ALLOWED_AUDIO_SEC = 40` (`pipeline.py` line 61); `assert_max_length` (lines 137-145) raises `ValueError("Max audio length is capped at 40s")` on longer files. `inference/README.md` recommends <= 30 s because models were mostly trained on <= 30 s audio.
  - `[REPO]` All four R-0034 test sets already satisfy <= 30 s: Swivuriso `dev_test` is filtered to 1-30 s (`runs/R-0019/swivuriso_summary.json`), FLEURS test is filtered to <= 30 s (1,034 clips, max 29.4 s, `runs/R-0019/eval_fleurs/predictions.jsonl`), NCHLT test max is 14.4 s (`runs/R-0019/eval_nchlt/predictions.jsonl`), and Soapies utterances are short dialogue turns (`src/soapies.py`).
- `[SOURCE]` **CTC decoding behavior (`pipeline.py` lines 310-331):** Greedy CTC decoding only (`torch.argmax` over logits per frame, collapse consecutive duplicates, drop blank/special tokens via `token_decoder(decoded_ids)`). No beam search or external language model is used by `ASRInferencePipeline` for CTC.

### 2.2 What v2 CTC output text looks like and scoring-fairness traps

- `[SOURCE]` **Direct inspection of Meta's SentencePiece tokenizer files (`rc_models_v2.yaml`, `rc_models_v1.yaml`, `wav2vec2_asr/config.py`, and in-memory protobuf parse of `omniASR_tokenizer.model` vs `omniASR_tokenizer_written_v2.model`):**
  - **v1 (`omniASR_tokenizer.model`, 9,812 tokens):** 0 ASCII uppercase letters (`A-Z`), 26 ASCII lowercase letters (`a-z`), 10 digits (`0-9`), and only 5 ASCII punctuation characters. (This is why GitHub Issue #46 noted the initial v1 checkpoint lacked capitalization.)
  - **v2 (`omniASR_tokenizer_written_v2.model`, 10,288 tokens, used by `omniASR_CTC_300M_v2` and `omniASR_CTC_1B_v2`):** adds 495 symbols and removes 19, giving **all 26 ASCII uppercase letters (`A-Z`)**, all 26 lowercase letters (`a-z`), **all 10 digits (`0-9`)**, **31 ASCII punctuation marks** (period, comma, question mark, exclamation mark, colon, semicolon, quotes, apostrophe, hyphen, slash, parentheses, brackets, currency/math symbols), **typographic/curly apostrophes and quotes (`U+2019`, `U+2018`, `U+02BC`, `U+201C`, `U+201D`)**, en/em dashes, and **236 accented Latin characters** (`U+00C0` to `U+024F`).
  - **No non-speech tags:** Maintainer `@jeanm` confirmed in Issue #47 that `<laugh>`, `<hesitation>`, `<unintelligible>`, and `<noise>` were stripped before training and are not in the tokenizer.
  - **Digits in output:** Maintainer `@mattsetz` confirmed in Issue #44 that models can emit digits (example output `"11:35 p m"`), though Issue #44 also noted some checkpoints/inputs drop digits because commissioned data guidelines spelled out numbers (`arXiv:2511.09690v1` Appendix C.2).

- `[REPO]` / `[INFERENCE]` **What makes scoring CTC v2 with `src/scoring.py` `normalise()` fair vs unfair:**
  Look at `src/scoring.py` lines 15-20:
  - It strips `[bracketed]` tags, applies Unicode NFC, lowercases, replaces `[^\w\s']` with a space (keeping letters, digits, and ASCII straight apostrophe `'`), replaces `_` with a space, and collapses whitespace.
  - **Fair (handled cleanly):** Capitalization (`A-Z` -> `a-z`), sentence-final punctuation (`. , ?`), and ASCII hyphens (`e-Afrika` -> `e afrika`, matching `decisions.md` D-0010).
  - **Unfair Trap 1: Curly apostrophes (`U+2019`, `U+2018`, `U+02BC`).** Because `omniASR_tokenizer_written_v2.model` includes `U+2019` and `U+2018`, any curly apostrophe emitted by Meta v2 is replaced with a **space** by `[^\w\s']`, splitting words (`don’t` -> `don t`, `nding’umntu` -> `nding umntu`), whereas `src/scoring.py` keeps straight `'`.
  - **Unfair Trap 2: Digits vs spelled-out numbers.** `[REPO]` Inspection of `runs/R-0019/eval_fleurs/predictions.jsonl` shows **200 of 1,034 FLEURS test references (19.3%) contain digits** (0 of 2,770 in NCHLT test). `scoring.normalise()` keeps digits verbatim (`\w`) and never equates `"2009"` with spelled-out isiXhosa number words. Because Thetha trained on FLEURS `train` (which uses digits like `ka-2009`, `decisions.md` D-0010) while Meta trained heavily on spelled-out-number guidelines (Appendix C.2) plus mixed corpora, a pure written-vs-spoken number style difference scores as 100% wrong on both WER and CER.
  - **Unfair Trap 3: Punctuation inside abbreviations and times (`p.m.`, `U.S.`, `11:35`).** Replacing `.` and `:` with spaces splits `"p.m."` into `"p m"` (two tokens), inflating WER if the reference wrote `"pm"`.
  - **Unfair Trap 4: Diacritics or non-Latin characters.** Because CTC has no language conditioning across 10,288 symbols, if it occasionally emits an accented Latin letter or non-Latin symbol on noisy clips, `normalise()` preserves it (unlike ASCII-only references). That is a genuine model error, not a normaliser bug, but worth counting in diagnostics.
  - **Recommended R-0034 scoring rule `[INFERENCE]`:**
    1. Report primary WER/CER with **unchanged `src/scoring.py` `v1`** so scores align with all past runs (`R-0001` to `R-0032`).
    2. Add a secondary diagnostic table for R-0034 reporting: (a) scores after mapping `U+2018`/`U+2019`/`U+02BC` -> `'` before `normalise()`, (b) **FLEURS digit-free subset (834 clips)** vs **FLEURS digit subset (200 clips)**, (c) **`cer_no_spaces`** on Soapies (already computed in `src/eval_soapies.py`) so hyphen/word-splitting differences are visible, and (d) count of non-ASCII characters emitted by Meta CTC v2.

### 2.3 CPU support, memory, and compute recommendation for R-0034

- `[SOURCE]` **CPU support and dtype quirk:** `pipeline.py` line 193 automatically falls back to `device="cpu"` when CUDA is absent, **but defaults to `dtype=torch.bfloat16`** (line 157). In GitHub Issue #57, a user found **`dtype=torch.float32` ran 2-3x faster than `float16` on CPU**, and maintainer `@artemru` confirmed CPU inference was not specifically optimized and reduced-precision CPU kernels may be unoptimized. On Windows, `README.md` notes `fairseq2` needs manual `libsndfile` setup.
- `[SOURCE]` / `[INFERENCE]` **Expected memory and speed:**
  - From `README.md` Model Architectures table:
    - `omniASR_CTC_300M_v2`: 325.5M params, **1.3 GiB** FP32 checkpoint, **~2 GiB** VRAM (BF16, batch=1, 30 s, A100), RTF 0.001 (~96x faster than 7B LLM). On CPU in FP32, expect roughly **2 to 3 GiB RAM** at `batch_size=1-4` `[INFERENCE]`.
    - `omniASR_CTC_1B_v2`: 975.1M params, **3.7 GiB** FP32 checkpoint, **~3 GiB** VRAM (BF16, batch=1, 30 s, A100), RTF 0.002 (~48x faster than 7B LLM). On CPU in FP32, expect roughly **5 to 6.5 GiB RAM** at `batch_size=1-4` `[INFERENCE]` (tight on the 15 GB laptop next to other apps, P-0013).
  - `[INFERENCE]` **Recommendation for R-0034:** Run both `omniASR_CTC_300M_v2` and `omniASR_CTC_1B_v2` on a **Linux GPU node (`g6.xlarge` L4 24 GB at $0.805/h, BF16)** rather than CPU. All four test sets total ~16.5 hours of audio; at CTC's non-autoregressive GPU speed, both models should finish in minutes (total cost **< $0.40** including boot and S3 sync), avoiding Windows `fairseq2` setup friction and laptop memory limits. If CPU latency must be measured later (as in R-0032), run a small timed subset separately on Linux CPU testing `float32` vs `bfloat16`.

---

## 3. Question 3: Loop Guards with a Fine-Tuned Whisper

### 3.1 How `faster-whisper` implements loop guards and silence skipping

- `[SOURCE]` Direct inspection of `faster-whisper` `v1.2.1` (`faster_whisper/transcribe.py`, matching the `faster-whisper 1.2.1` version used in `runs/R-0032/run.md`) and OpenAI's reference `openai/whisper/whisper/transcribe.py` + `arXiv:2212.04356v1` Section 4.5 shows the exact decoding control flow in `WhisperModel.transcribe`:
  - **Defaults (`transcribe.py` lines 747-783):** `beam_size=5`, `best_of=5`, `temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0]`, `compression_ratio_threshold=2.4`, `log_prob_threshold=-1.0`, `no_speech_threshold=0.6`, `condition_on_previous_text=True`, `without_timestamps=False`, `vad_filter=False`.
  - **Fallback loop (`generate_with_fallback`, lines 1432-1530):**
    1. At `temperature=0.0`, it runs beam search (`beam_size`, `patience`).
    2. At `temperature > 0.0`, it abandons beam search and runs **unconstrained random sampling** (`beam_size=1`, `num_hypotheses=best_of`, `sampling_topk=0`, `sampling_temperature=temperature`).
    3. It triggers fallback (`needs_fallback=True`) if `compression_ratio > compression_ratio_threshold` (using `len(utf8_bytes) / len(zlib.compress(utf8_bytes))`, line 1881) **OR** `avg_logprob < log_prob_threshold`.
    4. Exception (lines 1507-1513): if `no_speech_prob > no_speech_threshold` **AND** `avg_logprob < log_prob_threshold`, it cancels fallback and treats the window as silence.
    5. If all temperatures fail (lines 1517-1528), it returns the candidate with highest `avg_logprob` among results that stayed below `compression_ratio_threshold` (or among all results if none did).
  - **Segment skip check (`generate_segments`, lines 1215-1236):** After fallback, if `no_speech_prob > no_speech_threshold` AND NOT (`avg_logprob > log_prob_threshold`), it **skips the entire 30 s window and emits empty output**.
  - **Warning on `BatchedInferencePipeline` (`transcribe.py` lines 316-317):** Its docstring explicitly warns that for `temperature`, *"If a list or tuple is passed, only the first value is used."* It does NOT perform temperature fallback.

### 3.2 Four documented failure modes on fine-tuned Whisper models

1. `[SOURCE]` / `[REPO]` **`without_timestamps=False` (default) breaks models fine-tuned with `<|notimestamps|>`:**
   - `[REPO]` `src/train.py` lines 66-68 trained every Thetha model exclusively with prefix `<|startoftranscript|><|sw|><|transcribe|><|notimestamps|>`, never with timestamp tokens.
   - `[SOURCE]` Timmel et al. (`arXiv:2412.15726v3`, Section 4.3, Table 5) proved that sentence-level Whisper fine-tuning without timestamps causes severe timestamp/segmentation forgetting (long-form SubER degraded from 30.63 to 51.34 on SRG TV speech and 39.12 to 55.44 on phone conversations).
   - `[SOURCE]` `faster-whisper` Issues `#337`, `#1085`, and `#1212` document fine-tuned models producing hallucinated extra segments, 50% extra words, or empty sequences unless `without_timestamps=True` is forced (and `word_timestamps=False`).
2. `[SOURCE]` / `[REPO]` **`no_speech_prob` becomes uncalibrated after full fine-tuning without `<|nospeech|>`:**
   - `[REPO]` `src/train.py` (line 201) and `src/swivuriso.py` (line 75) drop every clip with an empty transcript, so R-0019 saw zero `<|nospeech|>` targets during 4,000 full-parameter updates.
   - `[SOURCE]` In `faster-whisper` Issue `#1085`, a fine-tuned Hindi `whisper-small` model emitted `no_speech_prob = 1.36e-14` (effectively zero). Similarly, OpenAI's pruned/fine-tuned `large-v3-turbo` outputs `no_speech_prob` around `1e-11` (`faster-whisper` Issues `#1028` and `#1128`).
   - `[REPO]` / `[INFERENCE]` Because `no_speech_prob` is uncalibrated, it fails in both directions: on real silence it stays near 0 and fails to stop hallucinations (`runs/R-0023/run.md`: R-0019 emitted `"i"` on 5 s of silence and `"c"` on 5 s of quiet noise), while if a fine-tune ever spikes `no_speech_prob > 0.6` on an uncertain clip (`avg_logprob < -1.0`), `faster-whisper` silently deletes the entire utterance.
3. `[SOURCE]` / `[INFERENCE]` **`log_prob_threshold=-1.0` triggers stochastic sampling on hard non-looping clips:**
   - `[SOURCE]` In `faster-whisper` Issue `#40`, author `@guillaumekln` confirmed that when temperature fallback triggers, random sampling makes output non-deterministic across runs and *"there is no guarantee that it will fully resolve the repetitions."* In Issue `#1168`, a user's fine-tuned Whisper jumped from 3.09% CER (SpeechBrain deterministic decoding) to 7.04% CER with heavy hallucinations under default `faster-whisper` settings (`temperature=[0.0..1.0]`, `log_prob_threshold=-1.0`, `condition_on_previous_text=True`).
   - `[INFERENCE]` On hard accented Swivuriso clips or code-switched Soapies TV dialogue (where R-0019 has 29.29% CER, `runs/R-0030`), genuine uncertainty pushes `avg_logprob` below `-1.0` even when the transcript is NOT looping. Setting `log_prob_threshold=-1.0` causes `faster-whisper` to discard the beam-search transcript and sample randomly at `T=0.2..1.0` (with `sampling_topk=0`), risking gibberish or extra errors. Setting **`log_prob_threshold=None`** restricts fallback strictly to actual repetition loops (`compression_ratio > 2.4`).
4. `[REPO]` / `[SOURCE]` **`condition_on_previous_text=True` (default) hurts R-0019 and spreads loops:**
   - `[REPO]` R-0023 (`runs/R-0023/run.md`) directly proved that passing previous text (`<|startofprev|>`) to R-0019 (never trained with prompts) worsened WER by **+1.36 to +1.70 points** (30.38% -> 31.74% / 32.08%) and caused silence to transcribe as prompt words.
   - `[SOURCE]` `faster-whisper` Issues `#40` and `#1168` confirm disabling `condition_on_previous_text=False` stops loops from propagating across windows.
5. `[REPO]` **Avoid `repetition_penalty > 1.0` and `no_repeat_ngram_size > 0`:**
   - `[REPO]` R-0026 (`runs/R-0026/run.md`) already tested `repetition_penalty=1.1` + `no_repeat_ngram_size=4` on R-0019 ("guards only"): it **worsened NCHLT dev WER from 30.38% to 31.74% (+1.36) and CER from 4.43% to 4.61%**, because isiXhosa words naturally repeat syllables and prefixes. Keep defaults (`repetition_penalty=1.0`, `no_repeat_ngram_size=0`).

### 3.3 Concrete recommended `faster-whisper` settings

Always use `WhisperModel.transcribe(...)` (not `BatchedInferencePipeline`).

| Parameter | R-0033 Arm A (Greedy + Guard) | R-0033 Arm B (Beam 5 + Guard) | `src/live.py` (Live / Voice Notes) | Why |
|---|---|---|---|---|
| `language` / `task` | `"sw"` / `"transcribe"` | `"sw"` / `"transcribe"` | `"sw"` / `"transcribe"` | Matches `decisions.md` D-0007 |
| `beam_size` | **`1`** | **`5`** | **`5`** | Arm A isolates loop guard vs past greedy runs; Arm B matches live page (`R-0021`) |
| `without_timestamps` | `True` | `True` | `True` | Required: model trained only with `<|notimestamps|>` |
| `condition_on_previous_text` | `False` | `False` | `False` | Required: R-0023 proved prior text hurts R-0019 |
| `no_speech_threshold` | `None` | `None` | `None` | `<|nospeech|>` is uncalibrated after fine-tuning |
| `log_prob_threshold` | `None` | `None` | `None` | Stops random sampling on hard non-looping clips (especially Soapies) |
| `compression_ratio_threshold` | `2.4` | `2.4` | `2.4` | Triggers fallback only on actual repetition loops (`arXiv:2212.04356` Sec 4.5) |
| `temperature` | `(0.0, 0.2, 0.4, 0.6)` | `(0.0, 0.2, 0.4, 0.6)` | `(0.0, 0.2, 0.4, 0.6)` | Cap at `0.6` instead of `1.0` to avoid high-temperature gibberish `[INFERENCE]` |
| `best_of` | `5` | `5` | `5` | Picks highest-scoring sample if fallback triggers |
| `repetition_penalty` / `no_repeat_ngram_size` | `1.0` / `0` | `1.0` / `0` | `1.0` / `0` | R-0026 proved `1.1` / `4` hurt isiXhosa WER by +1.36 |
| `vad_filter` | `False` | `False` | **`True`** | Test clips are pre-segmented (VAD risks clipping quiet speech onsets); live recordings need Silero VAD to kill silence hallucinations (R-0023) and chunk >30 s audio at pauses |
| `max_new_tokens` | NCHLT/Soapies `96`, FLEURS `225`, Swivuriso `440` | Same | `225` (per <=30 s VAD chunk) | Matches `runs/R-0019/job.sh` and `src/eval_soapies.py`; note `4 + 440 = 444 <= 448` (`transcribe.py` line 1421) |

### 3.4 How to report R-0033 honestly vs past greedy GPU scores

- `[REPO]` / `[INFERENCE]` Follow `AGENTS.md`'s append-only rule (never edit prior `results.md` rows) and prevent conflating three separate variables (engine/precision, beam search, and loop guard):
  1. State engine and precision explicitly (`faster-whisper` CT2 `fp16` GPU or `int8` CPU vs `transformers` `fp16` GPU in `src/baseline.py`; recall R-0020/R-0031 measured a ~0.06 to 0.18 CER int8 gap on NCHLT unseen). Ideally run R-0033 on CT2 `float16` (GPU) or `float32`/`int8` (CPU) and note the exact `compute_type`.
  2. Report **both Arm A (`beam_size=1`, guarded) and Arm B (`beam_size=5`, guarded)** alongside R-0019's prior unguarded greedy scores so the loop guard's effect is isolated from beam search.
  3. Log **fallback telemetry** in `metrics.json`: count of clips where `segment.temperature > 0.0`, their clip IDs, their initial `compression_ratio`, and whether any valid non-looping clip false-triggered at `2.4` (if `0` clips trigger on R-0019, Arm A confirms zero regression from turning the guard on). Note that any clip triggering `temperature > 0` uses stochastic sampling and is not bit-exact across runs unless seeded.

---

## 4. Question 4: SpecAugment for Hugging Face Whisper Fine-Tuning

### 4.1 Exact config fields, defaults, and implementation in `transformers==4.46.3`

- `[REPO]` `requirements-gpu.txt` pins **`transformers==4.46.3`**.
- `[SOURCE]` Direct inspection of `huggingface/transformers` `v4.46.3` (`src/transformers/models/whisper/configuration_whisper.py` lines 229-235, `modeling_whisper.py` lines 93-185 and 1525-1625) and `openai/whisper-medium/config.json` (which omits all SpecAugment fields, so `WhisperConfig` defaults apply):

| Config Field | Default in `transformers==4.46.3` | Meaning in `modeling_whisper.py` |
|---|---|---|
| `apply_spec_augment` | **`False`** | Master switch. Checked at line 1536; masking also checks `self.training`, so it turns off automatically during eval. |
| `mask_time_prob` | **`0.05`** | Fraction of time axis masked. Number of spans = `int(mask_time_prob * input_length / mask_time_length + epsilon)` (line 133). |
| `mask_time_length` | **`10`** | Width of each time mask in **10 ms log-mel frames** (`10` = **100 ms**). |
| `mask_time_min_masks` | **`2`** | Minimum number of time-mask spans per clip when `mask_time_prob > 0`. |
| `mask_feature_prob` | **`0.0`** | **Frequency masking is OFF by default even when `apply_spec_augment=True`.** Spans = `int(mask_feature_prob * 80 / mask_feature_length + epsilon)`. |
| `mask_feature_length` | **`10`** | Width of each frequency mask in **mel bins** (out of `80` mel bins for `whisper-medium`, so `10` = 12.5% of frequency channels). |
| `mask_feature_min_masks` | **`0`** | Minimum number of frequency-mask spans per clip when `mask_feature_prob > 0`. |

- `[SOURCE]` **Where masking happens (`modeling_whisper.py` lines 1540-1565, 1615-1624):** `_mask_input_features` runs on the raw `(batch_size, 80, 3000)` log-mel `input_features` **before** `self.encoder(...)` (`conv1`/`conv2`), setting masked entries to **`0`** (`input_features[mask_time_indices] = 0`, `input_features[mask_feature_indices] = 0`).
- `[SOURCE]` / `[REPO]` **Critical builder trap (`attention_mask` forwarding):**
  - `[SOURCE]` In `_compute_mask_indices` (lines 147-151), if `attention_mask` is `None`, `input_lengths` defaults to `sequence_length = 3000` (all 30 seconds). On a 4-second NCHLT clip, 2,600 of 3,000 frames are silence padding, so ~87% of random time masks land harmlessly on padding instead of real speech.
  - `[SOURCE]` Hugging Face fixed this exact bug in PR `#21298` and PR `#25983` (`examples/pytorch/speech-recognition/run_speech_recognition_seq2seq.py` lines 472-495): when `apply_spec_augment=True` and `mask_time_prob > 0`, the data loader passes `return_attention_mask=True` to `WhisperFeatureExtractor` (which returns a 3,000-frame mask matching actual audio length) and forwards `attention_mask` into `WhisperForConditionalGeneration.forward(..., attention_mask=attention_mask)` (verified at `modeling_whisper.py` line 1769).
  - `[REPO]` `src/train.py` lines 85 and 127 currently omit `return_attention_mask=True` and do not pass `attention_mask` in `Collator`. The builder MUST add `return_attention_mask=True` in `Clips.__getitem__` and pad/pass `attention_mask` in `Collator` whenever SpecAugment is enabled, and verify in a 2-step smoke test that `attention_mask.shape == (batch_size, 3000)` and works cleanly in `bf16` (note: because `input_features[mask] = 0` mutates `input_features` in-place, verify no autograd issue if `gradient_checkpointing` is ever enabled).

### 4.2 Values used in published Whisper work

- `[SOURCE]` **OpenAI Whisper Large-v2 (`arXiv:2212.04356v1`, Table 18)** and **Timmel et al. (`arXiv:2412.15726v3`, Section 3.2, Swiss German `whisper-large-v2` fine-tuning on 502 to 908 h):** Both applied SpecAugment with Park et al. (2019, `arXiv:1904.08779`, Table 1) **"LibriSpeech Basic" (LB)** policy: time warping `W=80` (not implemented in HF Whisper), frequency mask max width `F=27` mel bins (`m_F=1`, uniform in `[0, 27]` -> mean ~13.5 bins = ~17% of 80 mel bins), and time mask max width `T=100` frames (`1.0 s`, `m_T=1`, `p=1.0`, uniform in `[0, 100]` -> mean 0.5 s). For Switchboard mild (`SM`), Park et al. used `F=15, m_F=2` and `T=70, p=0.2, m_T=2`.
- `[SOURCE]` **NB-Whisper (`arXiv:2402.01917v1`, `NbAiLab/nb-whisper-medium/config.json`)** and **KB-Whisper (`KBLab/kb-whisper-medium/config.json`):** Both kept `apply_spec_augment=false` (trained on 50,000+ hours where overfitting is minimal; NB-Whisper used `activation_dropout=0.1` and BPE dropout `0.2`).
- `UNVERIFIED`: No peer-reviewed paper opened in this task published an ablation table comparing exact Hugging Face `mask_time_prob`/`mask_feature_prob` values specifically for `whisper-medium` on ~310 h.

### 4.3 Recommended SpecAugment settings for `whisper-medium` on ~310 h (R-0035)

- `[INFERENCE]` Mapping Park et al.'s mild-to-basic masking intensity onto Hugging Face's fixed-span formula (`int(prob * length / mask_length + epsilon)`), while keeping time spans short enough (100 ms) not to wipe out brief isiXhosa click bursts (`c`, `q`, `x`):
  - `model.config.apply_spec_augment = True` (plus `attention_mask` forwarded from `feature_extractor`)
  - `model.config.mask_time_prob = 0.05` (HF default: masks ~5% of real speech frames; e.g., ~2 spans of 100 ms on a 4 s clip, ~7 to 8 spans on a 15 s clip)
  - `model.config.mask_time_length = 10` (100 ms per span; HF default)
  - `model.config.mask_time_min_masks = 2` (HF default; guarantees at least 200 ms masked on short 2-3 s clips)
  - **`model.config.mask_feature_prob = 0.10`** (or `0.15`)
  - **`model.config.mask_feature_length = 8`** (8 of 80 mel bins = 10% of spectrum per mask)
  - **`model.config.mask_feature_min_masks = 1`**
  - **Math check against `modeling_whisper.py` line 133:** At `mask_feature_prob=0.10`, `mask_feature_length=8`, `0.10 * 80 / 8 = 1.0`, giving exactly 1 frequency band of 8 mel bins (10% of mel bins) masked per clip; at `0.15`, `0.15 * 80 / 8 = 1.5`, giving 1 or 2 bands (10% to ~19% of mel bins, matching Park et al. LB's ~17% mean frequency coverage without zeroing 27 contiguous bins). Start conservatively with **`mask_feature_prob = 0.10`, `mask_feature_length = 8`, `mask_feature_min_masks = 1`** (or `0.15` if the lead prefers slightly stronger frequency regularization). Keep `dropout` / `activation_dropout` at `0.0` so R-0035 does not stack unapproved extra changes.

---

## 5. Question 5: Training Length and Learning-Rate Schedule

### 5.1 Evidence from this repository's own `whisper-medium` runs

- `[REPO]` `src/train.py` lines 165-170 and 308-311 used `--lr 1e-5`, `--warmup 500`, `--max-steps 4000`, `lr_scheduler_type="linear"`, effective batch `32` (`8 x 4` on L40S), `bf16=True`, `weight_decay=0.0` (HF default) across R-0012, R-0019, and R-0029:

| Run | Data (hours / clips) | Steps / Epoch | Epochs at 4,000 steps | Final Train Loss | FLEURS Dev Loss Trajectory (steps 500 -> 4000) | Dev CER Trajectory (NCHLT / FLEURS) |
|---|---|---|---|---|---|---|
| **R-0012** (`runs/R-0012/model/`) | 64.23 h / 45,703 | 1,428 | **2.80 ep** | 0.058 | `0.793 -> 0.615 -> 0.544 -> 0.526 -> 0.489 -> 0.507 -> 0.508 -> 0.506` (plateaued at ~1.75-2.80 ep) | NCHLT `5.92 -> 2.66`; FLEURS `13.42 -> 7.79` |
| **R-0019** (`runs/R-0019/model/`) | 210.82 h / 78,100 | 2,441 | **1.64 ep** | 0.155 | `0.682 -> 0.520 -> 0.464 -> 0.430 -> 0.415 -> 0.405 -> 0.400 -> 0.391` (still falling every eval) | NCHLT `6.17 -> 2.91`; FLEURS `11.84 -> 6.37` |
| **R-0029** (`runs/R-0029/model/`) | 309.68 h / 98,663 | 3,083 | **1.30 ep** | 0.153 | `0.666 -> 0.517 -> 0.460 -> 0.437 -> 0.417 -> 0.392 -> 0.386 -> 0.382` (still falling every eval) | NCHLT `6.00 -> 2.99`; FLEURS `11.75 -> 6.40` |

- `[INFERENCE]` On 64.2 h *without* SpecAugment (R-0012), `whisper-medium` hit its FLEURS dev loss floor around **1.75 to 2.80 epochs** as training loss collapsed to `0.058`. On 309.7 h (4.8x more audio and 3x more speakers, 603 vs 196), R-0029 stopped at **1.30 epochs** while both training loss (`0.153`) and FLEURS dev loss (`0.382`) were still dropping cleanly when the linear LR reached zero. Adding SpecAugment (Q4) further slows memorization and typically shifts the dev minimum slightly later in epochs.

### 5.2 Published Whisper full fine-tuning schedules

- `[SOURCE]` **OpenAI Whisper (`arXiv:2212.04356v1`, Tables 17 & 19):** Pretraining `whisper-medium` used AdamW (`beta1=0.9`, `beta2=0.98`, `weight_decay=0.1`, max grad norm `1.0`), **linear decay** with warmup, peak LR **`2.5e-4`** (batch 256). Standard fine-tuning scales LR down 10x to 25x (`1e-5`).
- `[SOURCE]` **Hugging Face Whisper fine-tuning guide (`https://huggingface.co/blog/fine-tune-whisper`):** `learning_rate=1e-5`, `warmup_steps=500`, `max_steps=5000`, `batch=16`, linear decay (for ~10-20 h Common Voice Hindi).
- `[SOURCE]` **Swivuriso (`arXiv:2512.02201v3`, Sections 4.1-4.4, Tables 9-10):** Full fine-tuning of `whisper-large-v3-Turbo` (809M) used **`lr=1e-5`** with effective batch 32 for **10,000 steps** on multilingual Swivuriso (Table 9: WER fell from 37% at 1k steps to 15% at 10k steps) and batch 64 for 2,000 steps in cross-corpus runs. Their single-language 1-epoch scaling sweep (50/150/250 h, batch 64, `lr=1e-4`, Table 10) explicitly noted in Section 7 that fixed short budgets stopped before full convergence.
- `[SOURCE]` **Qian et al. (`arXiv:2407.06800`, Section 3.1):** Full fine-tuning of `whisper-large-v3` on unseen FLEURS languages used **`lr=1e-5` with linear decay**.
- `[SOURCE]` **BuzzASR (`arXiv:2609.09554v2`, Section 4.4 and Appendix B Tables 3-4):** On up to 100 h per language (10 h FLEURS + up to 90 h Common Voice) with `whisper-large-v3`, AdamW, batch 32-64, 150-200 warmup steps, and early stopping up to **6 epochs**, the 17-language Bayesian sweep optima clustered tightly around **`1.0e-5` to `2.0e-5`** (for example Italian `1.07e-5`, Catalan `1.58e-5`, Galician `1.65e-5`, Russian `1.77e-5`, Polish `1.87e-5`) across linear and cosine schedulers.
- `[SOURCE]` **Nahabwe et al. (`arXiv:2512.10968`):** Full fine-tuning of Whisper across 13 African languages (up to 50 h) used AdamW, **linear decay with 10% warmup**, batch 64, LR tuned in `[1e-5, 1e-3]`, and early stopping on validation loss.
- `[SOURCE]` **Distil-Whisper (`arXiv:2311.00430`, Appendix B.1 Table 15), Timmel et al. (`arXiv:2412.15726v3`, Table 2, 502-908 h), and NB-Whisper (`arXiv:2402.01917v1`, Tables 1-2):** All three used **linear decay with warmup**; their higher peak LRs (`1e-4` to `2e-4`) corresponded to 8x to 32x larger batch sizes (batch 256 to 1,024) or a frozen encoder (Distil-Whisper).

### 5.3 Recommendation and AWS cost table for R-0035

- `[INFERENCE]` **Recommended schedule for R-0035 (98,663 clips = 3,083 steps/epoch at batch 32):**
  - **`--max-steps 9000`** (**2.92 epochs**; fallback option `8000` steps = 2.59 epochs if capping spend strictly under $10 even on `g6e.2xlarge`). With `load_best_model_at_end=True` selecting on Swivuriso dev + FLEURS dev, running to 2.92 epochs lets us observe the actual validation trough (expected around ~2.0 to 2.8 epochs with SpecAugment) instead of stopping early again.
  - **`--lr 1e-5`**, **`--warmup 500`** (5.6% of 9,000 steps; already well-behaved in R-0012/R-0019/R-0029), **`lr_scheduler_type="linear"`** (matches OpenAI Whisper, HF, Qian et al., Timmel et al., NB-Whisper, and prior repo runs; no strong evidence that cosine beats linear here, and keeping linear avoids changing scheduler shape simultaneously with step count).
  - **`--eval-every 1000`** (9 checkpoints across 2.92 epochs, every 0.32 epochs; or `750` for 12 checkpoints every 0.24 epochs).
  - **`--max-hours 7`** (safety cap above the ~4.8-5.1 h expected runtime).
- `[REPO]` / `[INFERENCE]` **Cost projection from measured L40S throughput:**
  - In `runs/R-0029/model/log_history.json`, 4,000 steps took 7,119.3 s including 8 evaluations (~105.5 s each = ~844 s), giving **1.57 s/step** pure training on `g6e.2xlarge` (R-0019 on `g6e.xlarge`: **1.64 s/step**). Node overhead outside `train.py` (boot, S3 sync, memcheck, 3 test evals, S3 upload) was ~31 min (0.53 h) in R-0029.
  - Assuming ~135 s per eval (~480 Swivuriso dev + ~440 FLEURS dev, Q6) and ~31 min overhead (using R-0029's 1.57 s/step; `g6e.xlarge` is ~4% slower in steps, ~0.15 h extra):

| Steps (Epochs) | Pure Train Time | Total Wall Time (`eval@1000` / `eval@500`) | Est. Cost on `g6e.xlarge` ($1.861/h) | Est. Cost on `g6e.2xlarge` ($2.24/h) |
|---|---|---|---|---|
| 4,000 (1.30 ep, R-0029 ref) | 1.74 h | 2.42 h / 2.57 h | $4.51 / $4.78 | $5.42 / $5.76 |
| 6,000 (1.95 ep) | 2.61 h | 3.37 h / 3.59 h | $6.27 / $6.69 | $7.54 / $8.05 |
| 7,500 (2.43 ep) | 3.27 h | 4.08 h / 4.36 h | $7.59 / $8.11 | $9.13 / $9.76 |
| **9,000 (2.92 ep, recommended)** | **3.92 h** | **4.79 h / 5.12 h** | **$8.91 / $9.54** | **$10.72 / $11.48** |

- `[REPO]` / `[INFERENCE]` At `9,000` steps with `--eval-every 1000`, total R-0035 cost is **~$8.90 (`g6e.xlarge`) to ~$10.70 (`g6e.2xlarge`)**, fitting inside D-0031's ~$10-13 budget for Steps 1-3 combined (November GPU spend at D-0031 was $0.53 of the $30 brake). Prefer `g6e.xlarge` first with `g6e.2xlarge` fallback as in `runs/R-0029/run.md`.

---

## 6. Question 6: Checkpoint Selection on Swivuriso Dev + FLEURS Dev

### 6.1 How big a Swivuriso dev subset is needed for a stable CER signal

- `[REPO]` **What Swivuriso `dev` contains (`runs/R-0019/swivuriso_summary.json`):** After the 1-30 s and no-`[?]` filter, `dev` has **2,290 kept clips (8.20 h, 24 speakers)**, split into **5.88 h scripted (71.7%)** and **2.32 h unscripted (28.3%)**.
- `[SOURCE]` **Why speaker stratification matters most:** Liu & Peng (`arXiv:1912.09508v2`, "Statistical Testing on ASR Performance via Blockwise Bootstrap") show that utterances from the same speaker are statistically correlated, so ASR variance is governed by **speaker-level blocks** rather than independent clip counts.
- `[REPO]` **Measured speaker variance on Swivuriso's 24-speaker `dev_test` (`runs/R-0019/eval_swivuriso/metrics.json` and `runs/R-0029/eval_swivuriso/metrics.json`):**
  - Across the 24 speakers, clip counts range widely from **47 to 224 clips/speaker** (median 79.5), and R-0019 speaker CER varies **nearly 7x, from 1.7% to 11.8%** (mean 4.06%, SD = **2.35 percentage points**, SE across 24 speakers = 0.48 pp).
  - Crucially, for **paired checkpoint comparisons on the same fixed clips**, between-speaker difficulty cancels out: comparing R-0029 vs R-0019 across the 23 non-runaway speakers gives a speaker-level paired CER difference of **mean -0.191 pp, SD = 0.289 pp, SE = 0.060 pp**.
  - Mean reference length is **~151.5 characters per clip** (implied from R-0019's 13,388 letter errors at 4.12% CER across 2,145 clips, `runs/R-0029/run.md`).
  - L40S eval speed at batch 32 (`runs/R-0019/eval_swivuriso/metrics.json`): **203.9 s for 2,145 clips = 0.095 s/clip**.
- `[INFERENCE]` **Recommended Swivuriso dev subset: 480 to 600 clips (20 to 25 clips per speaker across ALL 24 speakers, fixed seed):**
  - **Never subsample speakers** (dropping half the 24 speakers inflates cluster variance by 41%). Always include **all 24 dev speakers**.
  - **Stratify by `(speaker, type)`** rather than naive uniform sampling: take up to **20 to 25 clips per speaker** (480 to 600 clips total, ~73,000 to 91,000 reference characters), drawing roughly **half scripted and half unscripted where available** (or up to 10-12 unscripted per speaker + remainder scripted) so unscripted speech is well represented instead of being outnumbered ~3:1 by scripted clips.
  - At 480 to 600 stratified clips across all 24 speakers, finite-population subsampling error on a paired checkpoint delta is roughly **~0.06 to 0.07 pp CER SE** (comparable to the 0.060 pp speaker-level paired SE across the full 2,145-clip split), while costing only **~46 to 57 seconds per evaluation** on an L40S. (Going up to 720 clips = 30/speaker costs ~68 s and lowers subsampling error slightly further; scoring all 2,290 clips would cost ~217 s per eval.)

### 6.2 FLEURS dev size and a critical truncation bug to fix first

- `[SOURCE]` Direct query of Hugging Face's `google/fleurs` (`xh_za`) dataset info confirms `validation` (`dev`) has **only 446 clips total** (~440 clips <= 30 s).
- `[REPO]` R-0019 and R-0029 capped FLEURS dev at 200 clips (`--fleurs-dev-clips 200`, taking ~38.5 s per eval on L40S, `runs/R-0019/model/log_history.json`).
- `[INFERENCE]` **Score all ~440 FLEURS dev clips** (`--fleurs-dev-clips 500`, ~85 s per eval on L40S). It costs only ~46 extra seconds per eval and eliminates FLEURS dev subsampling noise completely.
- `[REPO]` **CRITICAL BUG CATCH (`--generation-max-length 96` in `runs/R-0019/job.sh` line 78 and `runs/R-0029/job.sh` line 81):**
  - `src/baseline.py` line 86 notes `"FLEURS sentences need up to ~145 tokens"`, and `runs/R-0019/job.sh` line 64 used `--max-new-tokens 440` for Swivuriso test. Passing `--generation-max-length 96` during training eval truncates long FLEURS and Swivuriso dev utterances, injecting artificial deletion errors into checkpoint selection.
  - **Fix for builder:** Set **`--generation-max-length 225`** (matching `src/train.py` line 177 default and FLEURS test eval) AND filter the Swivuriso dev subset to clips whose reference is **`<= 220` tokenizer tokens** so no valid dev reference is ever truncated at 225 tokens while simultaneously capping any greedy runaway during dev eval to 225 tokens instead of 440.

### 6.3 How to combine Swivuriso dev and FLEURS dev for checkpoint selection

- `[REPO]` In `src/train.py` lines 301-320, `eval_dataset` is passed as a `dict` (`{"nchlt": ..., "fleurs": ...}`), so Hugging Face `Seq2SeqTrainer` evaluates each key independently and emits `eval_<key>_cer`. It cannot select on a weighted combination of two keys out of the box.
- `[INFERENCE]` **Recommended combination rule:**
  - Primary selection metric: **`eval_combined_cer = 0.5 * eval_swivuriso_cer + 0.5 * eval_fleurs_cer`** (lower is better), computed by a small `Seq2SeqTrainer.evaluate()` subclass override (~6 lines) that appends `eval_combined_cer` to the returned metrics dict before `load_best_model_at_end` checks `metric_for_best_model="combined_cer"`.
  - **Why equal macro weight (`0.5 / 0.5`) rather than clip-weighted pooling:** Pooling ~600 Swivuriso clips and ~440 FLEURS clips together lets whichever set has more characters dominate; equal macro weighting gives both domains a guaranteed voice. Because FLEURS CER (~6.2%) is ~1.5x higher than Swivuriso CER (~4.0%), a 10% relative gain moves FLEURS by ~0.62 pp vs ~0.40 pp on Swivuriso (~60/40 relative weight), mildly favoring cross-domain generalization on FLEURS and guarding against overfitting to Swivuriso's recording app. (If strict 50/50 *relative* weight is preferred, `sqrt(eval_swivuriso_cer * eval_fleurs_cer)` is scale-invariant; `0.5 * (S + F)` is recommended for plain-English transparency in percentage points.)
  - **Keep NCHLT dev (info-only) and guard against single-clip runaways during greedy dev eval:**
    - Keep `nchlt` in `evals` (reduced to 300 clips or kept at 600) as an info-only regression watch so we see if NCHLT degrades.
    - Remember one 901-letter greedy runaway added +0.24 pp CER to 2,145 Swivuriso test clips in R-0029 (`runs/R-0029/run.md`); on 600 dev clips, one greedy runaway could add ~0.5 to 0.8 pp CER and mislead `load_best_model_at_end`. Therefore: (1) log `runaway_clips` (count of dev predictions with `len(hyp) > 2.5 * len(ref)` and `len(hyp) > 150`) alongside `cer` in `compute_metrics`, and (2) set `save_total_limit=3` (~26 GB of a 300 GB volume) so the lead can inspect `log_history.json` before finalizing.

---

## 7. UNVERIFIED List

Items that could not be confirmed from opened primary sources during this task:

1. **Exact Swivuriso / African Next Voices splits ingested by Meta Omnilingual ASR (`v1` and `v2`):** Neither `arXiv:2511.09690v1` nor `facebookresearch/omnilingual-asr` discloses whether Meta trained only on Swivuriso `train` (427.40 h) or also included `dev`, `dev_test`, or a pre-split partner delivery.
2. **Source breakdown of Meta's 598.8 `xho_Latn` training hours and Table 3's hour-sum discrepancy:** `arXiv:2511.09690v1` does not itemize its 150,100 h "LTPP, internal & licensed data" pool by corpus or language, so inclusion or exclusion of NCHLT (~56 h), NCHLT auxiliary, or Soapies inside that private/partner pool cannot be proven with 100% certainty (and Table 3's row sum of 177,700 h vs reported total 120,710 h remains unanswered in GitHub Issue #82).
3. **Training data differences between Omnilingual ASR `v1` and `v2`:** The Dec 2025 v2 release (`omniASR_CTC_*_v2`, `omniASR_LLM_*_v2`) is not covered in `arXiv:2511.09690v1` (posted 2025-11-12), and the repo does not publish a v2 training-data table or changelog beyond "improved accuracy (CER)" and the new `omniASR_tokenizer_written_v2` tokenizer.
4. **Actual runtime frequency of uppercase, punctuation, curly apostrophes, and digits emitted by `omniASR_CTC_300M_v2` / `1B_v2` specifically on isiXhosa audio:** Direct inspection of `omniASR_tokenizer_written_v2.model` proves those characters are in the output vocabulary, but exact emission frequency on Swivuriso/FLEURS/NCHLT/Soapies isiXhosa clips can only be observed once R-0034 runs.
5. **Exact CPU RAM and CPU throughput of `omniASR_CTC_300M_v2` / `1B_v2` (`float32` vs `bfloat16`):** Only A100 BF16 VRAM (`~2 GiB` / `~3 GiB`) and FP32 checkpoint sizes (`1.3 GiB` / `3.7 GiB`) are published in Meta's `README.md`; CPU RAM and speed estimates above are `[INFERENCE]`.
6. **Peer-reviewed SpecAugment ablation specifically for Hugging Face `whisper-medium` on ~310 h of a new language:** No opened paper reported an ablation table over `mask_time_prob` / `mask_feature_prob` in that exact regime; recommended values (`mask_time_prob=0.05`, `mask_feature_prob=0.10`, `mask_feature_length=8`) are `[INFERENCE]` calibrated from Park et al. (2019), OpenAI Large-v2, and `modeling_whisper.py`'s exact masking formula.
7. **Exact hours of isiXhosa in van Niekerk et al. (2017) OpenSLR32:** OpenSLR32 did not return within timeout in this task, so the exact hour count (~3 h) is left out of verified claims and only the citation in `arXiv:2511.09690v1` Section 3.3.1 is claimed.

---

## 8. Claims Ledger

| Claim | Type | Source / Repo Reference |
|---|---|---|
| Meta funded African Next Voices (citing Marivate et al., 2025) and trained `AllASR` on 7,200 h across 13 ANV languages | `[SOURCE]` | `arXiv:2511.09690v1` Sec 3.3.2 & Table 3 (`https://arxiv.org/html/2511.09690`) |
| Swivuriso received a Gates Foundation grant and a gift from Meta | `[SOURCE]` | `arXiv:2512.02201v3` Sec 10 (`https://arxiv.org/html/2512.02201`) |
| Swivuriso HF repo `dsfsi-anv/za-african-next-voices` created 2025-07-09; `xho` splits: `train` 62,786, `dev` 3,768, `dev_test` 3,639 | `[SOURCE]` | HF API (`https://huggingface.co/api/datasets/dsfsi-anv/za-african-next-voices`) & `arXiv:2512.02201v3` Table 3 |
| Swivuriso `XHO` total is 73,665 clips, 485 speakers, 504.28 h; `train` 427.40 h (407 spk), `dev` 25.18 h (24 spk), `dev_test` 25.60 h (24 spk) | `[SOURCE]` | `arXiv:2512.02201v3` Tables 2, 3, 4 (`https://arxiv.org/html/2512.02201`) |
| `facebook/omnilingual-asr-corpus` covers 348 languages and does not contain `xho` | `[SOURCE]` | Corpus card (`https://huggingface.co/datasets/facebook/omnilingual-asr-corpus/raw/main/README.md`) |
| `per_language_results_table_7B_llm_asr.csv` lists `xho_Latn` = 598.8 training hours, 4.9 CER | `[SOURCE]` | CSV (`https://raw.githubusercontent.com/facebookresearch/omnilingual-asr/main/per_language_results_table_7B_llm_asr.csv`) |
| Table 3 rows sum to 177,700 h vs printed total 120,710 h; CSV sums to 196,226.7 h | `[SOURCE]` | `arXiv:2511.09690v1` Table 3 & Issue #82 (`https://github.com/facebookresearch/omnilingual-asr/issues/82`) |
| Omnilingual ASR trained on FLEURS `train` and evaluated on FLEURS `dev`/`test`; does not cite NCHLT or Soapies | `[SOURCE]` | `arXiv:2511.09690v1` Sec 3.3.1, Tables 5-7, Table 18 (`https://arxiv.org/html/2511.09690`) |
| FLEURS splits have disjoint speakers between `train`/`dev` and `test`; `xh_za` has 3,466 train, 446 validation, 1,041 test examples | `[SOURCE]` | `arXiv:2205.12446v1` Sec 2.1 (`https://arxiv.org/html/2205.12446`) & HF datasets-server (`https://datasets-server.huggingface.co/info?dataset=google/fleurs&config=xh_za`) |
| 6,139 of 38,536 kept 1-30 s Swivuriso `train` clips repeat a `dev`/`dev_test` sentence; Thetha dropped them | `[REPO]` | `runs/R-0019/run.md`, `runs/R-0019/model/data_split.json`, `src/train.py` L220-232 |
| 2,259 of 2,770 NCHLT test clips (81.6%) repeat a training sentence; Soapies is test/dev only (D-0016) | `[REPO]` | `decisions.md` note 2026-10-17 & D-0016, `runs/R-0027/run.md` |
| `omniASR_CTC_*_v2` requires `omnilingual-asr==0.2.0`, Python 3.10-3.13 (3.12 tested), `libsndfile`, max 40 s audio, resamples to 16 kHz mono + `layer_norm` | `[SOURCE]` | `pyproject.toml`, `pipeline.py` L61-145, 414-472, `README.md`, Issues #50 & #52 (`https://github.com/facebookresearch/omnilingual-asr`) |
| `omniASR_CTC_*_v2` ignores `lang`; `"xho_Latn"` is in `lang_ids.py` for LLM models only | `[SOURCE]` | `pipeline.py` L596-597, `inference/README.md` Sec 3.1, `lang_ids.py` (`https://github.com/facebookresearch/omnilingual-asr`) |
| `omniASR_tokenizer_written_v2.model` (10,288 tokens) contains 26 ASCII uppercase (`A-Z`), 26 lowercase, 10 digits, 31 ASCII punctuation marks, curly quotes/apostrophes (`U+2018`/`U+2019`/`U+02BC`), and 236 accented Latin chars; v1 (9,812) had 0 ASCII uppercase | `[SOURCE]` | `rc_models_v2.yaml`, `wav2vec2_asr/config.py`, and direct vocab parse of `https://dl.fbaipublicfiles.com/mms/omniASR_tokenizer_written_v2.model` and `https://dl.fbaipublicfiles.com/mms/omniASR_tokenizer.model` |
| `<laugh>`, `<hesitation>`, `<unintelligible>`, `<noise>` were stripped from training and are not in the tokenizer | `[SOURCE]` | Issue #47 (`https://github.com/facebookresearch/omnilingual-asr/issues/47`) |
| `ASRInferencePipeline` defaults to `dtype=torch.bfloat16`; on CPU, `float32` was reported 2-3x faster than `float16` and CPU was not specifically optimized | `[SOURCE]` | `pipeline.py` L157 & Issue #57 (`https://github.com/facebookresearch/omnilingual-asr/issues/57`) |
| `omniASR_CTC_300M_v2` is 325.5M params / 1.3 GiB FP32 / ~2 GiB BF16 VRAM (RTF 0.001); `1B_v2` is 975.1M / 3.7 GiB / ~3 GiB VRAM (RTF 0.002) | `[SOURCE]` | `README.md` Model Architectures table (`https://raw.githubusercontent.com/facebookresearch/omnilingual-asr/main/README.md`) |
| FLEURS test has 200/1,034 clips with digits and 428/1,034 with hyphens; NCHLT test has 0/2,770 digits/hyphens/apostrophes; `src/scoring.py` keeps `'` and `\w` but turns other punctuation (including `U+2019`) to space | `[REPO]` | `src/scoring.py` L15-20, `runs/R-0019/eval_fleurs/predictions.jsonl`, `runs/R-0019/eval_nchlt/predictions.jsonl` |
| `faster-whisper v1.2.1` `WhisperModel.transcribe` defaults to `without_timestamps=False`, `condition_on_previous_text=True`, `temperature=[0.0..1.0]`, `compression_ratio_threshold=2.4`, `log_prob_threshold=-1.0`, `no_speech_threshold=0.6`; `BatchedInferencePipeline` uses only the first temperature value | `[SOURCE]` | `faster-whisper v1.2.1` `transcribe.py` L254-318, L747-783, L1215-1236, L1402-1530 (`https://raw.githubusercontent.com/SYSTRAN/faster-whisper/v1.2.1/faster_whisper/transcribe.py`) |
| Sentence-level Whisper fine-tuning without timestamps causes timestamp/segmentation forgetting; fine-tuned models show near-zero `no_speech_prob` (`1.36e-14`), hallucinations under default fallback/context, or empty outputs when `without_timestamps=False` | `[SOURCE]` | `arXiv:2412.15726v3` Sec 4.3 Table 5; `faster-whisper` Issues `#40`, `#337`, `#1028`, `#1085`, `#1128`, `#1168`, `#1212` |
| Feeding previous text to R-0019 worsened NCHLT dev WER by +1.36 to +1.70 and hallucinated on silence; `repetition_penalty=1.1` + `no_repeat_ngram_size=4` worsened NCHLT dev WER 30.38 -> 31.74 and CER 4.43 -> 4.61 | `[REPO]` | `runs/R-0023/run.md`, `runs/R-0026/run.md` |
| In `transformers==4.46.3`, Whisper SpecAugment defaults are `apply_spec_augment=False`, `mask_time_prob=0.05`, `mask_time_length=10`, `mask_time_min_masks=2`, `mask_feature_prob=0.0`, `mask_feature_length=10`, `mask_feature_min_masks=0`; masks apply on `(B, 80, 3000)` log-mel `input_features` before encoder and require `attention_mask` to avoid masking padding | `[SOURCE]` | `transformers v4.46.3` `configuration_whisper.py` L229-235, `modeling_whisper.py` L93-185, L1525-1624, L1767-1770, `run_speech_recognition_seq2seq.py` L472-495, PRs `#21298` & `#25983` |
| OpenAI Whisper Large-v2 and Timmel et al. (502-908 h) used Park et al. LibriSpeech Basic (`F=27, m_F=1, T=100, m_T=1`); NB-Whisper & KB-Whisper kept `apply_spec_augment=false` | `[SOURCE]` | `arXiv:2212.04356v1` Table 18; `arXiv:1904.08779` Table 1; `arXiv:2412.15726v3` Sec 3.2; HF `NbAiLab/nb-whisper-medium/config.json` & `KBLab/kb-whisper-medium/config.json` |
| R-0012 (64.2 h, 2.80 ep) plateaued on FLEURS dev loss around 1.75-2.80 ep; R-0019 (210.8 h, 1.64 ep) and R-0029 (309.7 h, 1.30 ep) had dev loss still falling at step 4,000; pure train step speed is 1.57 s/step (`g6e.2xlarge`) and 1.64 s/step (`g6e.xlarge`) | `[REPO]` | `runs/R-0012/model/log_history.json`, `runs/R-0019/model/log_history.json`, `runs/R-0029/model/log_history.json`, `runs/R-0019/run.md`, `runs/R-0029/run.md` |
| Published Whisper full fine-tuning on ~10-250+ h converges around `lr=1e-5` (batch 16-64) with linear decay and warmup; BuzzASR 17-language optima cluster at `1.0e-5` to `2.0e-5` with max 6 epochs | `[SOURCE]` | `arXiv:2212.04356v1` Tables 17 & 19; HF `fine-tune-whisper` blog; `arXiv:2512.02201v3` Sec 4.1-4.4; `arXiv:2407.06800` Sec 3.1; `arXiv:2609.09554v2` Sec 4.4 & App B; `arXiv:2512.10968` |
| Same-speaker ASR utterances are correlated, so speaker-block variance controls reliability; Swivuriso `dev` has 2,290 kept clips across 24 speakers (71.7% scripted, 28.3% unscripted); `dev_test` speaker CER spans 1.7% to 11.8% (SD 2.35 pp), while R-0029 vs R-0019 paired speaker diff SD (23 non-runaway spk) is 0.289 pp (SE 0.060 pp); L40S eval runs at 0.095 s/clip | `[SOURCE]` & `[REPO]` | `arXiv:1912.09508v2` (`https://arxiv.org/abs/1912.09508`); `runs/R-0019/swivuriso_summary.json`, `runs/R-0019/eval_swivuriso/metrics.json`, `runs/R-0029/eval_swivuriso/metrics.json` |
| R-0019 and R-0029 passed `--generation-max-length 96` to `src/train.py`, below FLEURS's ~145-token need and Swivuriso's 440-token test limit | `[REPO]` | `runs/R-0019/job.sh` L64 & L78, `runs/R-0029/job.sh` L74 & L81, `src/baseline.py` L86 |

---

## 9. Sources List (All Directly Opened in This Task)

1. Omnilingual ASR Team (Meta FAIR, Nov 2025). *Omnilingual ASR: Open-Source Multilingual Speech Recognition for 1600+ Languages* (`arXiv:2511.09690v1`): https://arxiv.org/html/2511.09690
2. Meta FAIR `omnilingual-asr` GitHub repository (`README.md`, `pyproject.toml`, `per_language_results_table_7B_llm_asr.csv`, `src/omnilingual_asr/models/inference/README.md`, `src/omnilingual_asr/models/inference/pipeline.py`, `src/omnilingual_asr/models/README.md`, `src/omnilingual_asr/cards/models/rc_models_v1.yaml`, `rc_models_v2.yaml`, `src/omnilingual_asr/models/wav2vec2_asr/config.py`, `src/omnilingual_asr/models/wav2vec2_llama/lang_ids.py`, `src/omnilingual_asr/datasets/utils/audio.py`, `workflows/dataprep/README.md`, `workflows/dataprep/text_tools.py`, `workflows/recipes/wav2vec2/asr/wer_calculator.py`): https://github.com/facebookresearch/omnilingual-asr
3. Meta Omnilingual ASR GitHub Issues & PRs:
   - PR #48 / #49 (v2 suite): https://github.com/facebookresearch/omnilingual-asr/pull/48 and https://github.com/facebookresearch/omnilingual-asr/pull/49
   - Issue #44 (digits): https://github.com/facebookresearch/omnilingual-asr/issues/44
   - Issue #46 (capitalization): https://github.com/facebookresearch/omnilingual-asr/issues/46
   - Issue #47 (special tags): https://github.com/facebookresearch/omnilingual-asr/issues/47
   - Issue #50 & #52 (v2 requires 0.2.0 / Python 3.12): https://github.com/facebookresearch/omnilingual-asr/issues/50 and https://github.com/facebookresearch/omnilingual-asr/issues/52
   - Issue #57 (CPU float32 vs float16): https://github.com/facebookresearch/omnilingual-asr/issues/57
   - Issue #71 (v1 vs v2): https://github.com/facebookresearch/omnilingual-asr/issues/71
   - Issue #82 (Table 3 corpus hour sum discrepancy): https://github.com/facebookresearch/omnilingual-asr/issues/82
   - Issue #87 (installing 0.2.0): https://github.com/facebookresearch/omnilingual-asr/issues/87
4. Meta Omnilingual ASR tokenizers (direct SentencePiece vocabulary inspection in memory): https://dl.fbaipublicfiles.com/mms/omniASR_tokenizer.model and https://dl.fbaipublicfiles.com/mms/omniASR_tokenizer_written_v2.model
5. Meta Omnilingual ASR Corpus dataset card (348 languages): https://huggingface.co/datasets/facebook/omnilingual-asr-corpus/raw/main/README.md
6. Marivate et al. (2025/2026). *Swivuriso: The South African Next Voices Multilingual Speech Dataset* (`arXiv:2512.02201v3`): https://arxiv.org/html/2512.02201
7. Swivuriso Hugging Face dataset metadata (`dsfsi-anv/za-african-next-voices`): https://huggingface.co/datasets/dsfsi-anv/za-african-next-voices and https://huggingface.co/api/datasets/dsfsi-anv/za-african-next-voices
8. Conneau et al. (2022/2023). *FLEURS: Few-shot Learning Evaluation of Universal Representations of Speech* (`arXiv:2205.12446v1`): https://arxiv.org/html/2205.12446 and HF split metadata: https://datasets-server.huggingface.co/info?dataset=google/fleurs&config=xh_za
9. Radford et al. (2022). *Robust Speech Recognition via Large-Scale Weak Supervision* (`arXiv:2212.04356v1`): https://arxiv.org/html/2212.04356
10. OpenAI `whisper` reference decoding (`whisper/transcribe.py`): https://raw.githubusercontent.com/openai/whisper/main/whisper/transcribe.py
11. SYSTRAN `faster-whisper` `v1.2.1` (`faster_whisper/transcribe.py`): https://raw.githubusercontent.com/SYSTRAN/faster-whisper/v1.2.1/faster_whisper/transcribe.py
12. SYSTRAN `faster-whisper` GitHub Issues:
    - Issue #40 (temperature fallback randomness & repetition): https://github.com/SYSTRAN/faster-whisper/issues/40
    - Issue #337 (`without_timestamps` on fine-tuned models): https://github.com/SYSTRAN/faster-whisper/issues/337
    - Issue #1028 & #1128 (`no_speech_prob` near 0 on turbo): https://github.com/SYSTRAN/faster-whisper/issues/1028 and https://github.com/SYSTRAN/faster-whisper/issues/1128
    - Issue #1085 (fine-tuned Hindi model `no_speech_prob = 1.36e-14` & extra segments): https://github.com/SYSTRAN/faster-whisper/issues/1085
    - Issue #1168 (fine-tuned model hallucinations/CER jump under default `faster-whisper`): https://github.com/SYSTRAN/faster-whisper/issues/1168
    - Issue #1212 (empty sequence on fine-tuned model): https://github.com/SYSTRAN/faster-whisper/issues/1212
13. Hugging Face `transformers` `v4.46.3` Whisper source & SpecAugment PRs:
    - `configuration_whisper.py`: https://raw.githubusercontent.com/huggingface/transformers/v4.46.3/src/transformers/models/whisper/configuration_whisper.py
    - `modeling_whisper.py`: https://raw.githubusercontent.com/huggingface/transformers/v4.46.3/src/transformers/models/whisper/modeling_whisper.py
    - `feature_extraction_whisper.py`: https://raw.githubusercontent.com/huggingface/transformers/v4.46.3/src/transformers/models/whisper/feature_extraction_whisper.py
    - `run_speech_recognition_seq2seq.py`: https://raw.githubusercontent.com/huggingface/transformers/v4.46.3/examples/pytorch/speech-recognition/run_speech_recognition_seq2seq.py
    - `openai/whisper-medium/config.json`: https://huggingface.co/openai/whisper-medium/raw/main/config.json
    - PR #21298 & PR #25983: https://github.com/huggingface/transformers/pull/21298 and https://github.com/huggingface/transformers/pull/25983
14. Park et al. (2019). *SpecAugment: A Simple Data Augmentation Method for Automatic Speech Recognition* (`arXiv:1904.08779`): https://arxiv.org/html/1904.08779
15. Hugging Face fine-tuning blog (Gandhi, 2022). *Fine-Tune Whisper For Multilingual ASR with Transformers*: https://huggingface.co/blog/fine-tune-whisper
16. Gandhi et al. (2023). *Distil-Whisper: Robust Knowledge Distillation via Large-Scale Pseudo Labelling* (`arXiv:2311.00430`): https://arxiv.org/html/2311.00430
17. Qian et al. (2024). *Learn and Don't Forget: Adding a New Language to ASR Foundation Models* (`arXiv:2407.06800`): https://arxiv.org/html/2407.06800
18. Kummervold et al. (2024). *Whispering in Norwegian: Navigating Orthographic and Dialectic Challenges* (`arXiv:2402.01917v1`): https://arxiv.org/html/2402.01917 and model configs: https://huggingface.co/NbAiLab/nb-whisper-medium/raw/main/config.json and https://huggingface.co/KBLab/kb-whisper-medium/raw/main/config.json
19. Timmel et al. (2025). *Fine-tuning Whisper on Low-Resource Languages for Real-World Applications* (`arXiv:2412.15726v3`): https://arxiv.org/html/2412.15726
20. Nahabwe et al. (2025). *Benchmarking Pre-Trained ASR Models on African Languages* (`arXiv:2512.10968`): https://arxiv.org/html/2512.10968
21. Singh et al. (2026). *BuzzASR: A Swarm of 100+ Monolingual Speech Recognition Models* (`arXiv:2609.09554v2`): https://arxiv.org/html/2609.09554
22. Liu & Peng (2020). *Statistical Testing on ASR Performance via Blockwise Bootstrap* (`arXiv:1912.09508v2`): https://arxiv.org/abs/1912.09508
