<!-- DRAFT for the founder to edit and post himself. -->

OpenAI's Whisper understands almost a hundred languages. isiXhosa isn't one of them.

So I taught it.

Over a few weeks I fine-tuned Whisper on about 64 hours of open isiXhosa speech (NCHLT and Google FLEURS), one
experiment at a time, on rented cloud GPUs. Total cloud bill: about $10.

Where it landed:
• Stock Whisper got 46 % of letters wrong on isiXhosa sentences it had never heard. My best model gets 8 %.
• It runs on an ordinary laptop CPU, with the same accuracy as on the GPU.
• It still struggles when people mix English into isiXhosa, the way most of us actually talk. "Stubborn" comes out as
  "istabhunga". That's the next problem worth solving.

Everything is open: the code, every experiment (including the ones that failed), the models, and a demo you can talk to
on your phone. Nothing you record is stored.

🎙️ Try it: https://ntlakanipho-thetha.static.hf.space
🤗 Model: https://huggingface.co/Ntlakanipho/whisper-medium-isixhosa
💻 Code and the full lab notebook: https://github.com/2Ntlaks/isixhosa-speech-ai

Credit to SADiLaR, CSIR Meraka, North-West University and Google for the open speech data that made this possible.

#isiXhosa #SpeechRecognition #AfricanLanguages #OpenSource #MachineLearning
