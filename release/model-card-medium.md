---
language:
- xh
license: cc-by-4.0
base_model: openai/whisper-medium
pipeline_tag: automatic-speech-recognition
library_name: transformers
datasets:
- google/fleurs
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
      value: 8.03
    - type: wer
      value: 37.83
  - task:
      type: automatic-speech-recognition
    dataset:
      name: NCHLT isiXhosa Speech Corpus (test)
      type: nchlt-isixhosa
      split: test
    metrics:
    - type: cer
      value: 2.33
    - type: wer
      value: 12.71
---

# whisper-medium-isixhosa

OpenAI's **whisper-medium** fine-tuned to transcribe **isiXhosa**, a language stock Whisper does not support. This is
run **R-0012** of an open learning project. Every experiment, failed ones included, is documented at
**https://github.com/2Ntlaks/isixhosa-speech-ai**.

**Try it:** {SPACE_URL}

## Scores

Lower is better. CER = share of letters wrong, WER = share of words wrong. isiXhosa words are long (one wrong letter
fails the whole word), so CER is the fairer headline.

| Test set | CER % | WER % | Note |
|---|---|---|---|
| **FLEURS xh_za test** (1 034 clips, read sentences never seen in training) | **8.03** | **37.83** | the fairest score |
| NCHLT isiXhosa test (2 770 clips, 8 speakers not in training) | 2.33 | 12.71 | flattering: 82 % of test clips repeat a training sentence |
| NCHLT test, unseen sentences only | 5.0 | 28.7 | |
| Soapies isiXhosa–English code-switched TV speech (391 clips) | 38.43 | 79.59 | conversational, mixed languages: weak |
| *Stock whisper-medium on FLEURS, for comparison* | *45.86* | *142.32* | |

The same light normalisation is used for every score: lowercase, punctuation removed, spelling untouched.

## How to use it

> **Important:** the model borrows Whisper's **Swahili tag** for isiXhosa. Always pass `language="sw"`. It writes
> isiXhosa, not Swahili.

```python
from transformers import pipeline

asr = pipeline("automatic-speech-recognition", model="{HF_USER}/whisper-medium-isixhosa")
print(asr("clip.wav", generate_kwargs={"language": "sw", "task": "transcribe"})["text"])
```

The `ct2-int8/` folder holds an 8-bit [CTranslate2](https://github.com/OpenNMT/CTranslate2) copy (742 MB instead of
3 GB) that runs on an ordinary laptop CPU with the same accuracy (run R-0013: CER 5.67 vs 5.69 on 200 clips). It powers
the demo; see `src/live.py` in the GitHub repository for how to call it.

## Training

- **Base:** `openai/whisper-medium` (769M parameters).
- **Data:** NCHLT isiXhosa Speech Corpus training split (51 h, read prompts) and Google FLEURS `xh_za` train (13 h, read
  sentences). 6 NCHLT training speakers were held out as a dev set to pick the checkpoint.
- **Recipe:** 4 000 steps, batch 32 (8 × 4 accumulation), learning rate 1e-5 with 500 warm-up steps and linear decay,
  bf16. One NVIDIA L40S, 2.1 GPU hours, about $3.90.
- **Target text:** lowercase, no punctuation. Hyphens after prefixes are written as spaces (`e afrika`, not `e-Afrika`).

## Limitations

- **Read speech only.** Fast conversation, background noise and unfamiliar accents are weak spots.
- **English inside isiXhosa** gets isiXhosa spelling ("stubborn" became "istabhunga" in the code-switched test).
- **No punctuation or capitals.** The model also tags its output as Swahili (see above).
- **About one word in three** has at least one wrong letter on new sentences. Check transcripts before relying on them.
- Not evaluated for any high-stakes use. Do not use it to identify speakers.

## Data and credits

- **NCHLT isiXhosa Speech Corpus**, CSIR Meraka Institute and North-West University, distributed by SADiLaR
  ([hdl.handle.net/20.500.12185/279](https://hdl.handle.net/20.500.12185/279)), CC BY 3.0.
- **Google FLEURS** `xh_za` ([google/fleurs](https://huggingface.co/datasets/google/fleurs)), CC BY 4.0.
- The code-switched score uses the Soapies corpus (van der Westhuizen & Niesler, LREC 2018), which is research only. It
  was used for testing only and never for training.
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
