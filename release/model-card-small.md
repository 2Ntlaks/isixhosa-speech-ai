---
language:
- xh
license: cc-by-4.0
base_model: openai/whisper-small
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
- name: whisper-small-isixhosa
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
      value: 8.89
    - type: wer
      value: 38.18
  - task:
      type: automatic-speech-recognition
    dataset:
      name: Swivuriso isiXhosa (dev_test, clips 1-30 s without [?])
      type: dsfsi-anv/za-african-next-voices
      config: xho
      split: dev_test
    metrics:
    - type: cer
      value: 5.25
    - type: wer
      value: 24.03
  - task:
      type: automatic-speech-recognition
    dataset:
      name: NCHLT isiXhosa Speech Corpus (test)
      type: nchlt-isixhosa
      split: test
    metrics:
    - type: cer
      value: 3.37
    - type: wer
      value: 21.56
---

# whisper-small-isixhosa

OpenAI's **whisper-small** fine-tuned to transcribe **isiXhosa** (run **R-0027** of
**https://github.com/2Ntlaks/isixhosa-speech-ai**). It is about 3× smaller and faster than
[whisper-medium-isixhosa](https://huggingface.co/{HF_USER}/whisper-medium-isixhosa), and a little less accurate.

> **Updated 22 October 2026:** retrained with ~245 hours of natural isiXhosa speech from Swivuriso, including long
> recordings cut into pieces at the pauses between words. The previous version (R-0007) is still available:
> `revision="R-0007"`.

**Try it in your browser:** {SPACE_URL} (this model, running on your own device; nothing is uploaded)

**Read how it was made:** [I taught an AI to understand isiXhosa](https://ntlaks.dev/writing/teaching-whisper-isixhosa/), an interactive write-up with the real recordings, training curves and every stage of the project.

Lower is better. CER = share of letters wrong, WER = share of words wrong.

| Test set | CER % | WER % | Previous version (R-0007) |
|---|---|---|---|
| **Swivuriso test, people speaking in their own words** (723 clips) | **5.1** | **23.0** | 11.8 / 47.4 |
| **Swivuriso test, all** (2 145 clips of 1–30 s, 24 speakers of its own) | **5.25** | **24.03** | 9.88 / 42.49 |
| **FLEURS xh_za test** (1 034 clips, sentences not in training) | **8.89** | **38.18** | 10.16 / 44.38 |
| NCHLT isiXhosa test (2 770 clips) | 3.37 | 21.56 | 2.91 / 16.80 |
| NCHLT test, sentences not in training (511 clips) | 5.3 | 33.3 | 5.8 / 34.9 |

NCHLT got slightly worse only on sentences that repeat its training prompts: with much more natural speech in training,
the model memorises those read prompts less. On new sentences it is better on every test.

```python
from transformers import pipeline

asr = pipeline("automatic-speech-recognition", model="{HF_USER}/whisper-small-isixhosa")
print(asr("clip.wav", generate_kwargs={"language": "sw", "task": "transcribe"})["text"])
```

Always pass `language="sw"`: the model borrows Whisper's Swahili tag for isiXhosa. Two 8-bit copies are included:
`ct2-int8/` (CTranslate2, 240 MB, for CPUs) and `onnx/` (ONNX for [transformers.js](https://github.com/huggingface/transformers.js),
295 MB, what the browser demo runs). Run R-0028: on 200 unseen NCHLT test sentences the ONNX copy scores CER 6.07 and the
CTranslate2 copy 5.95, against 5.91 for the original.

**Training:** `openai/whisper-small`, 4 000 steps, batch 32, learning rate 1e-5 (500 warm-up steps). Data, 309.7 h:
NCHLT isiXhosa train (51 h, read prompts), FLEURS `xh_za` train (13 h), and Swivuriso isiXhosa train (245.4 h,
407 speakers): 146.6 h of clips of 1–30 s, plus 98.9 h cut from recordings longer than 30 s (forced alignment with
torchaudio's MMS aligner, cut at the widest pause before 28 s, checked with the medium model before training).
Clips with unclear speech (`[?]`) and any clip containing a test or dev sentence were left out. One NVIDIA L4, 3.9 hours
of machine time (about $3).

**Limitations:** no punctuation or capitals; about one word in four (natural speech) to one in three (read news
sentences) has a slip. English words inside isiXhosa are written in English, but it sometimes guesses an English word too
eagerly (the name "Thetha" came out as "theatre"). Clips longer than 30 s are transcribed in 30 s pieces. Not evaluated
for high-stakes use; do not use it to identify speakers.

**Credits:** NCHLT isiXhosa Speech Corpus (CSIR Meraka Institute and North-West University, via SADiLaR, CC BY 3.0);
Google FLEURS (CC BY 4.0); **Swivuriso, South Africa African Next Voices**
([dsfsi-anv/za-african-next-voices](https://huggingface.co/datasets/dsfsi-anv/za-african-next-voices)), isiXhosa part, by
the South Africa NextVoices team (Data Science for Social Impact, University of Pretoria), CC BY 4.0. The dataset's terms
allow speech recognition and prohibit text-to-speech, voice cloning and voice synthesis; respect them when you use this
model. Base model openai/whisper-small (MIT). Weights released under **CC BY 4.0**.
