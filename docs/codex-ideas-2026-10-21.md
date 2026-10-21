# Thetha: independent recommendations, 21 October 2026

Sections 1-5 were written before reading Claude's document. **My guess** labels hypotheses, proposed thresholds and cost estimates, not demonstrated gains.

## 1. Diagnosis and cheap tests

- **Measured (R-0021, aggregate recount):** 149 substitutions, 9 deletions and 4 insertions across 586 reference words; 111/149 aligned substitutions differ by only 1-2 character edits. Only 8/200 clips differ solely in spacing. **My guess:** a spelling dictionary alone will struggle with valid but incorrect words and unfamiliar names.
- **My guess, A:** the decoder prefers a familiar English completion when the sound is ambiguous; the founder's unnumbered prompt probe suggests this, but does not establish that Swivuriso caused it. Freeze new founder-corrected recordings, compare R-0012/R-0019 with identical decoding, and inspect five alternatives. Test relevant versus unrelated context lists prepared before recording, never extracted from test answers. Get the actual reference before counting the suspected shuttle error.
- **My guess, B:** reduced sounds, missing context and chunk boundaries are separate possibilities. Compare the original phrase with surrounding audio, a pause-preserving crop, and pitch-preserving 0.9x playback separately. Inspect microphone clipping. `live.py:85-96` cuts at 30 seconds and caps output at 225 tokens: test boundary shifts and cap hits separately. These cannot explain a short phrase far from either limit. Long recordings are not necessarily fast; measure speaking rate before prioritizing all 235 unused hours.
- **Measured (R-0020):** int8 CER 5.01 versus fp16 4.95 on the same sample. **My guess:** changing precision is low priority.

## 2. No-retraining fixes, ranked

1. **My guess:** expose useful alternative words on request, beside replay of the disputed audio. Keep beam 5; return five hypotheses instead of discarding four. Expected gain: easier human correction if the right word survived search; risk: all candidates share a mistake. Measure candidate recovery, correction time, final WER/CER and latency. Cost: $0 cloud, extra CPU work to measure. [CTranslate2 API](https://opennmt.net/CTranslate2/python/ctranslate2.models.Whisper.html#ctranslate2.models.Whisper.generate).
2. **My guess:** short, user-entered vocabulary for this recording only, with an unprompted comparison and undo. Expected gain: names/English terms; risk: vocabulary intrudes where absent. Measure target recovery AND false insertions on unrelated audio and silence, plus WER/CER. Cost: $0 cloud; comparison adds decoding work. Never globally replace tether with Thetha.
3. **My guess:** pause-aware chunks with small overlaps, sequential processing and duplicate removal. Expected gain: recording edges and long-file usability; risk: duplicate or missing words. Measure errors near joins and end-to-end time/RAM, not just `compute_seconds`. Cost: $0 cloud, overlap overhead. Audit token-cap truncation independently before raising limits.

## 3. Retraining below $10, ranked

**My guess:** use paired 500-step continuations from R-0019: control unchanged, candidate changes only the item below; both lr 2e-6, warmup 50, effective batch 32, bf16, same seed/evaluation. Estimate $3-8 per pair using cached data, anchored to **measured (R-0019)** $5.53 for the full job. Require founder approval and a total $9 stop budget including evaluation/storage; estimates are not quotes.

1. **My guess:** double sampling weight of existing, fully transcribed unscripted Swivuriso training clips. Expected gain: conversational errors without alignment expense; risk: read-speech regression. Measure fast-speech dev WER/CER, English-term errors and unchanged corpus tests against the control.
2. **My guess:** prompt robustness training: 50% unprompted, 25% short relevant lists, 25% unrelated lists, using training-transcript words only; mask prompt tokens from loss. Expected gain: controlled vocabulary support; risk: learning to copy hints. Measure unprompted accuracy and irrelevant-hint insertions as well as prompted accuracy. Preserve the existing transcription prefix.

**My guess:** defer the full long-clip expansion. First align a small, diverse training-only pilot; listen-check accepted AND rejected segments. Selecting only segments R-0019 already transcribes correctly would discard the difficult speech we need. No Soapies training; no invented transcripts.

## 4. Useful products now, ranked

1. **My guess:** a correction desk for interviews/voice notes: click a phrase to replay its audio, choose an alternative, undo, export. Existing upload/edit/copy is the starting point. Success: less time to an accurate transcript than manual transcription, tested with a few consenting users.
2. **My guess:** a local, searchable voice-note inbox with resumable jobs and search results linked to original audio. Useful even when some words are wrong; retain only with consent. Before promising privacy, remove transcript printing from `live.py:172`, including public-mode logs.
3. **My guess:** creator captions with editable timing and SRT export, after checking alignment quality. Measure editing time and missed words; names, amounts and negation deserve explicit review, not automatic rewriting. Keep a literal transcript separate from any later polished version.

## 5. The ONE experiment first

**My guess:** a five-candidate recovery audit. Freeze 100 NCHLT dev clips plus 20 new, consented founder clips before seeing outputs; reserve existing tests for later confirmation. Change only `num_hypotheses=1` to `5`, keeping beam 5, limits and prompts fixed. Report top-choice WER/CER and the best candidate per clip selected using the reference, an optimistic ceiling, NOT achieved accuracy. Pass to a correction-UI trial if that ceiling improves WER by at least 3 absolute points, top-choice WER/CER do not worsen, and latency stays within 1.25x baseline. Otherwise reject this route. Estimated $0 cloud, under an hour sequentially on CPU. No claims about unseen users from this small pilot.

## 6. After reading Claude

**My guess:** agree on scoped vocabulary, correction collection and rejecting blind replacements. Disagree that more fast speech is already established as "the real fix": diagnose missing sounds versus candidate ranking first. Empty-context tests cannot reveal harm from irrelevant nonempty prompts. A word-list rescoring system needs the candidate-recovery audit first and must protect valid rare/English words. Alignment-quality filtering also needs rejected-segment audits. I would defer translation: measure transcript correction value before adding another source of meaning errors. Claude missed the output-cap/chunk audit, public transcript logging, and reusable alternatives with audio replay. **Measured (R-0021):** 14 clips improved and 9 worsened; the completed run supports a small sample gain, not a claim of reliable improvement everywhere.
