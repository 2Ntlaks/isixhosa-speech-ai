---
title: Thetha · isiXhosa speech to text
emoji: 🎙️
colorFrom: yellow
colorTo: red
sdk: static
app_file: index.html
license: mit
short_description: Speak isiXhosa, see the text. Runs in your browser.
models:
- Ntlakanipho/whisper-small-isixhosa
custom_headers:
  cross-origin-embedder-policy: require-corp
  cross-origin-opener-policy: same-origin
  cross-origin-resource-policy: cross-origin
---

# Thetha

Speak isiXhosa and see it written. [whisper-small-isixhosa](https://huggingface.co/Ntlakanipho/whisper-small-isixhosa)
runs **inside your browser** (about 300 MB, downloaded once), so **nothing you record leaves your device**.

Read the story: https://ntlaks.dev/writing/teaching-whisper-isixhosa/

Code and every experiment: https://github.com/2Ntlaks/isixhosa-speech-ai

Built with [transformers.js](https://github.com/huggingface/transformers.js) 3.0.2 (Apache-2.0), served from this Space so
it can use several CPU threads.
