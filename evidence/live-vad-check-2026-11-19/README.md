# Live page: voice activity filter (VAD) on vs fixed 30 s cuts (2026-11-19, builder, laptop, $0)

Not a numbered run (no run ID was reserved for it); evidence for the live page change in `src/live.py`.

- **Question:** does the live page's Silero VAD (silence dropped, speech cut into pieces of at most 30 s at pauses)
  change accuracy, compared with the old fixed 30.0 s cuts? Both with the loop guard and beam 5.
- **Rule set before running:** keep VAD on by default if its CER is at most 0.3 worse than fixed cuts on BOTH sets.
- **Model:** the published small model, R-0027 (`Ntlakanipho/whisper-small-isixhosa` @ `f06d9358`, ct2-int8), laptop
  CPU, through `src/live.py`'s own `transcribe()` (the medium does not fit next to other work in laptop memory).
- **Clips:** FLEURS xh_za test (Hugging Face google/fleurs @ `70bb2e84`). (a) 120 short clips, seeded (2026), none of
  the 40 used in the first check; (b) 15 long recordings, each 3-4 other test clips joined with 1-3 s of silence,
  36-70 s, where fixed cuts can fall mid-word. Script: `vad_check.py` (run from the repo root with the scratch paths
  of that session; FLEURS audio is not in git).

| | short clips (120) WER / CER | long recordings (15) WER / CER |
|---|---|---|
| fixed 30 s cuts | 36.50 / 7.96 | 45.27 / 17.55 |
| **VAD pieces** | 36.75 / **7.89** | 44.96 / **11.93** |

- **Clip by clip (CER):** short: VAD better on 32, worse on 37, same on 51 (no real difference); long: better on 10,
  worse on 5. **PASS: VAD stays on.** The gain is where it was expected: long recordings that fixed cuts split
  mid-word. The loop guard fired once (a long recording's middle piece repeated itself; the 0.4 sample was kept).
- An earlier, smaller check (40 clips + 1 recording) pointed both ways; this one replaces it.
