# Lead verification of Neon's two reports (Claude, 2026-11-19)

Method: every repo claim checked against the files; external claims checked by opening the sources
(about 60 numbers in the review, about 40 in the pre-flight memo). Verdict per report below.
Use the reports together with these corrections.

## neon-first-principles-review-2026-11-19.md
- All 26 sources exist and are real. All repo claims confirmed (epochs 2.80 / 1.64 / 1.30 / 1.30 for R-0012 / R-0019 /
  R-0027 / R-0029; R-0027 kept checkpoint-3500; src/train.py line 306 selects on nchlt_cer; SPEC.html line 120).
- Census 2022 figures confirmed in the PDF (16.3 % national, 81.8 % Eastern Cape, 31.4 % Western Cape).
- Corrections:
  - Azure lists xh-ZA only in its LLM Speech / fast transcription table, not standard speech-to-text.
  - Omnilingual Table 22: 50 % language conditioning is the paper's "best tradeoff", not best in either mode.
  - Swivuriso Table 6 (NCHLT model 71 % on Swivuriso) is pooled over seven languages; splits are in Table 3, not 2.
  - BuzzASR is "Findings of EMNLP 2026"; Amharic 49.39 -> 9.07 is SFT -> FFT (tokenizer plus multitask).
  - Nahabwe's LM table is labelled Table 1; Luganda/Shona LM numbers could not be re-read (page truncation).
  - MMS 6.1 % CER on FLEURS Xhosa is an adapter model fine-tuned on FLEURS with a FLEURS LM, not mms-1b-all as released.
  - Gain sizes for the "drastic" paths (-15 to -25 WER) are Neon's estimates with no evidence.
- Missed by Neon, added by the lead: Omnilingual trained on African Next Voices, so Swivuriso test overlap must be checked.

## neon-preflight-2026-11-19.md
- Repo claims confirmed, including a real bug: R-0019/R-0027/R-0029 job.sh passed --generation-max-length 96 to
  train.py, so dev-set outputs used for checkpoint selection were capped at 96 tokens.
- Code claims confirmed in source: transformers 4.46.3 SpecAugment defaults (off; feature masking 0.0) and that
  _compute_mask_indices uses the full 30 s length when attention_mask is None; faster-whisper v1.2.1 accepts None for
  log_prob/no_speech thresholds, and BatchedInferencePipeline uses only the first temperature and never checks
  compression ratio.
- Omnilingual: CTC models "don't support language conditioning"; files must be shorter than 40 s (except the
  LLM Unlimited models); facebook/omnilingual-asr-corpus has no isiXhosa; GitHub issue #82 (hour totals do not add up)
  is open and unanswered. Which African Next Voices splits Meta used remains UNVERIFIED either way.
- Corrections:
  - faster-whisper #1168: 3.09 % CER (SpeechBrain) is right, but 7.04 % is the BatchedInferencePipeline run (which
    reduced hallucination); the default faster-whisper run was 10.22 %.
  - faster-whisper #1085: confirms no_speech_prob 1.36e-14 on a fine-tune; the thread is about word_timestamps, not
    without_timestamps. (without_timestamps=True is still right: our models were trained with <|notimestamps|>.)
  - large-v3-turbo no_speech_prob is about 3e-11 to 1e-10, not "around 1e-11".
  - Timmel et al. confirmed; their SubER numbers use WhisperX VAD timestamps.
  - Whisper large-v2 used SpecAugment (confirmed); the table number "18" was not verified.
- Settings adopted for R-0033 to R-0035 are sent to the builder (see JOURNAL 2026-11-19).

## Overall verdict on Neon
Real sources and accurate numbers, strong code reading (found the 96-token bug and the attention_mask trap), honest
UNVERIFIED lists. Weak spot: details of secondary sources (issue threads, table labels) are sometimes misattributed,
and conclusions are stated more firmly than the sources allow. Check its secondary citations before relying on them.
