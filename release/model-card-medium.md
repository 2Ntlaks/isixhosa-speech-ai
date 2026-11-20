---
language:
- xh
license: cc-by-4.0
base_model: openai/whisper-medium
pipeline_tag: automatic-speech-recognition
library_name: transformers
datasets:
- google/fleurs
- dsfsi-anv/za-african-next-voices
tags:
- whisper
- isixhosa
- xhosa
- speech-recognition
- african-languages
- low-resource
model-index:
- name: whisper-medium-isixhosa
  results:
  - task:
      type: automatic-speech-recognition
    dataset:
      name: FLEURS xh_za (test)
      type: google/fleurs
      config: xh_za
      split: test
    metrics:
    - type: cer
      value: 5.56
    - type: wer
      value: 26.64
  - task:
      type: automatic-speech-recognition
    dataset:
      name: Swivuriso isiXhosa (dev_test, clips 1-30 s without [?])
      type: dsfsi-anv/za-african-next-voices
      config: xho
      split: dev_test
    metrics:
    - type: cer
      value: 3.38
    - type: wer
      value: 15.51
  - task:
      type: automatic-speech-recognition
    dataset:
      name: NCHLT isiXhosa Speech Corpus (test)
      type: nchlt-isixhosa
      split: test
    metrics:
    - type: cer
      value: 1.99
    - type: wer
      value: 11.45
---

# whisper-medium-isixhosa

OpenAI's **whisper-medium** fine-tuned to transcribe **isiXhosa**, a language stock Whisper does not support. This is
run **R-0035** of an open learning project. Every experiment, failed ones included, is documented at
**https://github.com/2Ntlaks/isixhosa-speech-ai**.

> **Updated 20 November 2026:** retrained on more data (309.7 h) with a better recipe: trained about twice as long,
> SpecAugment, and the checkpoint chosen on natural speech. Fewer errors on every test set. The previous versions are
> still available: `revision="R-0019"` (October 2026) and `revision="R-0012"`.

**Try it:** https://ntlakanipho-thetha.static.hf.space/index.html (runs the smaller [whisper-small-isixhosa](https://huggingface.co/Ntlakanipho/whisper-small-isixhosa) in your browser)

**Read how it was made:** [I taught an AI to understand isiXhosa](https://ntlaks.dev/writing/teaching-whisper-isixhosa/), an interactive write-up with the real recordings, training curves and every stage of the project.

## Scores

Lower is better. CER = share of letters wrong, WER = share of words wrong. isiXhosa words are long (one wrong letter
fails the whole word), so CER is the fairer headline. Two ways of decoding are shown, each against the previous version
(R-0019) decoded the same way:

- **Plain:** `transformers`, greedy, as in the code example below (the numbers in the metadata above).
- **Guarded:** beam 5 with Whisper's own repetition fallback, on CTranslate2 (`faster-whisper`); this is how the
  project now scores every model (run R-0033).

| Test set | Plain CER / WER | R-0019 plain | Guarded CER / WER | R-0019 guarded | Note |
|---|---|---|---|---|---|
| **FLEURS xh_za test** (1 034 clips) | **5.56 / 26.64** | 6.24 / 30.32 | **5.21 / 26.06** | 5.75 / 28.92 | test sentences never seen in training; FLEURS's train split *is* in training |
| **Swivuriso test, people speaking in their own words** (723 clips) | **3.0 / 13.8** | 4.1 / 19.0 | **2.8 / 13.4** | 3.8 / 18.0 | home ground: same recording project as most of the training data |
| Swivuriso test, all (2 145 clips of 1-30 s, 24 speakers) | 3.38 / 15.51 | 4.12 / 19.12 | 3.24 / 15.04 | 3.92 / 18.26 | short, fully transcribed clips only |
| NCHLT isiXhosa test (2 770 clips, 8 speakers not in training) | 1.99 / 11.45 | 2.31 / 13.67 | 1.92 / 11.11 | 2.23 / 13.48 | flattering: 82 % of clips repeat a training sentence |
| NCHLT test, unseen sentences only (511 clips) | 4.3 / 25.5 | 4.4 / 26.6 | 4.1 / 24.4 | 4.1 / 26.3 | the NCHLT gain is mostly on sentences also in training |

The same light normalisation is used for every score: lowercase, punctuation removed, spelling untouched. On
isiXhosa-English code-switched TV speech (Soapies test, research-only corpus, never trained on) it is still weak:
guarded CER 25.98 / WER 60.84 (R-0019: 27.08 / 63.37).

## How to use it

> **Important:** the model borrows Whisper's **Swahili tag** for isiXhosa. Always pass `language="sw"`. It writes
> isiXhosa, not Swahili.

```python
from transformers import pipeline

asr = pipeline("automatic-speech-recognition", model="Ntlakanipho/whisper-medium-isixhosa")
print(asr("clip.wav", generate_kwargs={"language": "sw", "task": "transcribe"})["text"])
```

The `ct2-int8/` folder holds an 8-bit [CTranslate2](https://github.com/OpenNMT/CTranslate2) copy (775 MB instead of
3 GB) that runs on an ordinary laptop CPU (`faster-whisper`, `language="sw"`, `beam_size=5`). The 8-bit copy costs a
little accuracy: on 100 FLEURS test clips, CER 6.16 with ctranslate2 4.5.0 (6.32 with 4.8.1) against 5.97 at full
precision; no loss on NCHLT (runs R-0036, R-0037). See `src/live.py` in the GitHub repository for how to call it.

## Training

- **Base:** `openai/whisper-medium` (769M parameters).
- **Data (309.7 h, 98 663 clips, 603 speakers):**
  - NCHLT isiXhosa Speech Corpus training split (51.2 h, read prompts).
  - Google FLEURS `xh_za` train (13.0 h, read sentences).
  - Swivuriso isiXhosa train (245.4 h of read and unscripted speech from 407 speakers): clips of 1-30 s, plus 98.9 h
    of pieces cut from longer clips at word timings. Clips whose transcript marks unclear speech (`[?]`) were dropped.
    Any clip whose sentence appears in a test or dev set was removed (6 139 clips).
- **Recipe:** 9 000 steps (about 2.9 passes over the data), batch 32 (8 x 4 accumulation), learning rate 1e-5 with 500
  warm-up steps and linear decay, bf16. SpecAugment (time and frequency masks, training only). The checkpoint (step
  8 000) was chosen on the average CER of a Swivuriso dev sample (528 clips, 24 speakers) and FLEURS dev (441 clips);
  neither is trained on. One NVIDIA L40S, 4.6 h of training (~5.5 h of machine time, about $12).
- **Target text:** lowercase, no punctuation. Hyphens after prefixes are written as spaces (`e afrika`, not `e-Afrika`).

## Limitations

- **Long and fast speech.** It was trained on clips of 30 s or less. Fast, run-together speech is still a weak spot.
- **English inside isiXhosa.** It writes English words in English, but code-switched speech is still hard (see the
  Soapies score above), and it sometimes guesses an English word too eagerly.
- **No punctuation or capitals.** The model also tags its output as Swahili (see above).
- **About one word in four** has at least one wrong letter on new read sentences (NCHLT unseen, FLEURS). Check
  transcripts before relying on them.
- Not evaluated for any high-stakes use. Do not use it to identify speakers.

## Data and credits

- **NCHLT isiXhosa Speech Corpus**, CSIR Meraka Institute and North-West University, distributed by SADiLaR
  ([hdl.handle.net/20.500.12185/279](https://hdl.handle.net/20.500.12185/279)), CC BY 3.0.
- **Google FLEURS** `xh_za` ([google/fleurs](https://huggingface.co/datasets/google/fleurs)), CC BY 4.0.
- **Swivuriso, South Africa African Next Voices** ([dsfsi-anv/za-african-next-voices](https://huggingface.co/datasets/dsfsi-anv/za-african-next-voices)),
  isiXhosa part, by the South Africa NextVoices team (Data Science for Social Impact, University of Pretoria), CC BY 4.0.
  The dataset's terms allow speech recognition and prohibit text-to-speech, voice cloning and voice synthesis. Respect
  those terms when you use this model.
- The code-switched score uses the Soapies corpus (van der Westhuizen & Niesler, LREC 2018), which is research only.
  It was used for testing only and never for training.
- Base model: [openai/whisper-medium](https://huggingface.co/openai/whisper-medium) (MIT).

These weights are released under **CC BY 4.0**. Credit "Ntlakanipho Mgaguli, isiXhosa Speech AI" and the datasets above.

## Citation

```bibtex
@software{mgaguli_isixhosa_speech_ai_2026,
  author = {Mgaguli, Ntlakanipho},
  title  = {isiXhosa Speech AI: fine-tuning Whisper for isiXhosa},
  year   = {2026},
  url    = {https://github.com/2Ntlaks/isixhosa-speech-ai}
}
```
