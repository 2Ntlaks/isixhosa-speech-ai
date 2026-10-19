---
language:
- xh
license: cc-by-4.0
base_model: openai/whisper-small
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
      value: 10.16
    - type: wer
      value: 44.38
  - task:
      type: automatic-speech-recognition
    dataset:
      name: NCHLT isiXhosa Speech Corpus (test)
      type: nchlt-isixhosa
      split: test
    metrics:
    - type: cer
      value: 2.91
    - type: wer
      value: 16.80
---

# whisper-small-isixhosa

OpenAI's **whisper-small** fine-tuned to transcribe **isiXhosa** (run **R-0007** of
**https://github.com/2Ntlaks/isixhosa-speech-ai**). It is about 3× smaller and faster than
[whisper-medium-isixhosa](https://huggingface.co/{HF_USER}/whisper-medium-isixhosa), and a little less accurate.

**Try it:** {SPACE_URL} (choose "small")

| Test set | CER % | WER % |
|---|---|---|
| **FLEURS xh_za test** (1 034 clips, unseen sentences) | **10.16** | **44.38** |
| NCHLT isiXhosa test (2 770 clips; most sentences also occur in training) | 2.91 | 16.80 |
| Soapies isiXhosa–English code-switched TV speech (391 clips) | 42.13 | 87.97 |

```python
from transformers import pipeline

asr = pipeline("automatic-speech-recognition", model="{HF_USER}/whisper-small-isixhosa")
print(asr("clip.wav", generate_kwargs={"language": "sw", "task": "transcribe"})["text"])
```

Always pass `language="sw"`: the model borrows Whisper's Swahili tag for isiXhosa. `ct2-int8/` holds an 8-bit
CTranslate2 copy (240 MB) for CPUs.

**Training:** `openai/whisper-small`, 4 000 steps, batch 32, learning rate 1e-5. Data: NCHLT isiXhosa train (51 h) and
FLEURS `xh_za` train (13 h). One NVIDIA L4, 2.4 GPU hours.

**Limitations:** these are the same as the medium model's: read speech only, English words get isiXhosa spelling, no
punctuation, and about one word in two has a slip on new sentences.

**Credits:** NCHLT isiXhosa Speech Corpus (CSIR Meraka Institute and North-West University, via SADiLaR, CC BY 3.0),
Google FLEURS (CC BY 4.0), base model openai/whisper-small (MIT). Weights released under **CC BY 4.0**.
