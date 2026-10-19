<!-- DRAFT for ntlaks.dev. The founder edits it into his own voice before publishing. Every number cites a run. -->

# I taught Whisper to hear isiXhosa for about $10

OpenAI's Whisper is one of the best speech recognisers in the world, and it speaks almost a hundred languages.
isiXhosa, spoken by more than eight million South Africans, isn't one of them. Ask it to transcribe isiXhosa and it
guesses Swahili, Yoruba or Shona, or switches to another alphabet entirely.

I wanted to understand speech AI properly, so I set myself a project: make Whisper write isiXhosa, keep a record of
every experiment, and spend as little as possible.

## Step 1: how bad is it?

On 2 770 isiXhosa test clips, stock Whisper got 75 % of letters wrong and more words wrong than there were words (WER
197 %), because it kept inventing text (R-0001). It guessed 52 different languages.

## Step 2: the first fine-tune

The NCHLT corpus from SADiLaR has about 56 hours of isiXhosa read aloud by about 200 speakers, free under CC BY. I
fine-tuned whisper-small on it for 4 000 steps on one cloud GPU: 2.3 hours, $1.85. Letters wrong dropped from 46 % to
3 % (R-0004).

Then I looked closer. 82 % of the test clips repeated a sentence that was also in training, so the model was partly
remembering. On new sentences from Google's FLEURS it scored 30 % letters wrong and glued words together, because NCHLT
is mostly short prompts (R-0005).

## Step 3: better data, bigger model

Adding 13 hours of FLEURS, which is full varied sentences, fixed the gluing: 30 % to 10 % (R-0007). Moving from
whisper-small to whisper-medium took it to **8 %** (R-0012). Converted to 8-bit, it runs on my laptop's CPU with the
same accuracy (R-0013). I built a small page, Thetha, where I can talk to it and watch it write.

## Step 4: where it breaks

Real people mix English into isiXhosa. On code-switched dialogue from South African soap operas, the model gets 38 %
of letters wrong (R-0014). It hears the English and spells it like isiXhosa: "stubborn" became "istabhunga". I designed
the fix (South African English plus joined isiXhosa–English clips), but haven't run it.

## What I learned

- **The test set decides what you think you've built.** The same model looked like 3 % or 30 % depending on whether the
  test sentences were new.
- **Data beats size, then size helps.** FLEURS did more than a 3× bigger model.
- **Write everything down.** 14 experiments, 14 problems and 19 decisions are logged with causes and costs. That record is
  most of what I learned.

Everything is open: code, run records, models and a demo.
- Demo: https://ntlakanipho-thetha.static.hf.space
- Model: https://huggingface.co/Ntlakanipho/whisper-medium-isixhosa
- Code: https://github.com/2Ntlaks/isixhosa-speech-ai

Thanks to SADiLaR, the CSIR Meraka Institute and North-West University (NCHLT), Google (FLEURS), and Stellenbosch
University (the soap-opera corpus, used for testing only).
