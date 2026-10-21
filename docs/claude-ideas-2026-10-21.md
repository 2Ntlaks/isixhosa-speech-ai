# How to make Thetha make fewer word mistakes, and be useful now (Claude, 2026-10-21)

Written before reading Codex's answer (docs/codex-ideas-2026-10-21.md), so the two can be compared fairly.
Nothing here is measured yet unless a run ID is given.

## The two error types the founder found

- **(a) English over-guessing**: "Thetha" -> "tether", probably "shuttle" -> "shackles". My guess (not tested): R-0019 learned from Swivuriso
  (which marks English words) that English words should be written in English. It now leans on Whisper's original
  English knowledge, and when a sound is close to a common English word, the English word wins.
- **(b) Fast, run-together speech**: "man ukuya" -> "amanye". Elided or reduced syllables in fast speech; the model
  picks a real word that fits the sound. More natural fast speech in training is the real fix.
- Background: about 1 word in 4 has a wrong letter, mostly 1-2 letters inside long words.

## No retraining (free, laptop only), ordered by what I would test first

1. **Beam search (R-0021, running).** Keeps the 5 best partial transcripts instead of 1. Usually a small, reliable
   gain on letter slips; costs extra CPU time in the decoder (the 30 s encoder, ~5 s, does not change).
2. **A personal word list ("hotwords") through Whisper's prompt.** Put "Thetha" and other names before the
   transcript as previous text. Risk: R-0019 was never trained with prompts, so it may ignore them or copy them in.
   Test on the founder's saved recordings and on 200 clips with an empty-context prompt to make sure nothing breaks.
3. **Rescoring beam candidates with an isiXhosa word list or small n-gram model.** The 5 beam candidates often differ
   by one letter; a model of which isiXhosa words and word pairs exist can pick the real one. Text: NCHLT and FLEURS
   transcripts (CC BY), isiXhosa Wikipedia (CC BY-SA). The Siyamthanda project used a
   word language model for Afrikaans as part of a larger measured gain, so this is promising. Must exclude every test sentence from the LM text.
4. **Not recommended:** a blind replacement list (tether -> Thetha) breaks real English. Suppressing English tokens
   would undo R-0019's main gain (English words written in English).

## Cheap retraining (< $10)

1. **Train with previous-text prompts** (Whisper's original training did this): randomly give the model the text of
   a preceding clip, or a list of names, as a prompt. Then hotword biasing (2 above) works by design.
2. **Swivuriso's long clips** (235 h, mostly natural, fast speech) -> fixes (b) most directly. Cutting needs word
   timings: run a CTC aligner (e.g. a multilingual MMS forced aligner) on audio + transcript, cut at pauses between
   words, keep only pieces whose alignment score is good, and listen to a sample before training.
3. **The founder's corrections** as a small, high-weight set; too few now to train on, so keep them as a test set first.

## Most useful for people now (my ranking)

1. **Voice notes in, text out**: the page already accepts WhatsApp audio; add automatic splitting of long audio at
   pauses so a 3-minute voice note works, with a copy button.
2. **isiXhosa -> English translation line** under the transcript (NLLB-200 knows isiXhosa; the Siyamthanda project
   already runs it on a laptop). Makes Thetha useful to people who do not speak isiXhosa.
3. **Subtitles (.srt) for videos**: same splitting plus timestamps.
4. **A correction loop that grows the test and training data** (already there: keep + correct).
