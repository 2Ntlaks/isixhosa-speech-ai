---
title: Thetha · isiXhosa speech to text
emoji: 🎙️
colorFrom: yellow
colorTo: red
sdk: docker
app_port: 7860
license: mit
short_description: Speak isiXhosa, see the text. Nothing is stored.
models:
- {HF_USER}/whisper-medium-isixhosa
- {HF_USER}/whisper-small-isixhosa
---

# Thetha

Speak isiXhosa and see it written. This runs [whisper-medium-isixhosa](https://huggingface.co/{HF_USER}/whisper-medium-isixhosa)
(more accurate) or [whisper-small-isixhosa](https://huggingface.co/{HF_USER}/whisper-small-isixhosa) (faster) on a
free CPU, so expect a few seconds per recording. **Nothing you record is stored.**

How it was made, with every experiment: https://github.com/2Ntlaks/isixhosa-speech-ai
