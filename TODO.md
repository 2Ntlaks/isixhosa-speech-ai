# To-do · Saturday 18 October 2026

Where we are: stage 3 is done. Best model **R-0012** (whisper-medium): 8.0 % letter errors on unseen long sentences
(FLEURS), 2.3 % on NCHLT. Thetha (the talk-to-it page) runs on the laptop. Next: **stage 4, your voice mixed with English.**

## Quick answers from you (5 minutes)

- [ ] **a friend's recordings:** is a friend happy for their clips in `data/my_voice/live/` to be kept and used as test
      data? If not, I delete them.
- [ ] **Tonight's 12 corrections:** count them as the first stage 4 test sentences, or start fresh?
- [ ] **GPU budget for stage 4 training:** raise the $20 monthly brake now, or wait for 1 November? (Recording and the
      test set need no GPU, so waiting is fine.)
- [ ] **Hyphens (D-0010):** should the model write `e-Afrika` (standard spelling) or `e afrika` (what it does now)?
      No rush; matters for stage 5.

## Agent prepares (before you record)

- [ ] **Stage 4 plan sheet** (`docs/stage4.png`): what to record, how many, test vs training split, consent, how a
      recording becomes test data.
- [ ] Update the progress page (`docs/progress.html`) with Thetha and R-0013.
- [ ] Optional: speed test on the laptop's Radeon graphics chip (`.venv-dml` is installed).

## You record (after the plan sheet)

- [ ] Start Thetha (PowerShell, in the project folder):
      ```
      $env:CT2_USE_MKL="0"; .venv\Scripts\python src\live.py
      ```
      then open http://127.0.0.1:7860. Keep the **keep** dot on.
- [ ] First batch: about **50 short recordings** in your own words, the way you really talk, isiXhosa with English
      mixed in. One sentence each, 3-15 seconds.
- [ ] Correct every transcript: click the text, fix it, press **Enter**. The corrected text is the "true text".

## Deploying (stage 5)

- [ ] **GitHub:** say yes and I create a **private** repository and push the project (backup + history). Recordings,
      models and audio stay out (gitignored). Before it ever goes public: check for things that shouldn't be public
      (e.g. the AWS account number in run records) and the dataset credits.
- [ ] **Hugging Face account** (you create it), then log in on the laptop yourself: type `! hf auth login` in the chat
      box. Never paste a token into the chat.
- [ ] Then the agent: model repo (R-0012 + 8-bit copy + honest model card) and a Space (Thetha online, works on phones).

## When you have time

- [ ] Listening page verdicts: open `data/listen/listen-R-0012.html`, judge the clips, press **Copy my notes**,
      paste them to me.


## Future work

- **isiXhosa -> English translation** (D-0015): train Whisper itself on FLEURS isiXhosa audio + the official English
  text, after stage 4. ~$4 GPU run. Measure against FLEURS's English before showing it; launch it labelled
  "English, experimental" next to transcription, never instead of it.
