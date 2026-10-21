# R-0023 · "My words" harm check: do word lists leak into transcripts where they don't belong? (laptop, R-0019-int8)

- **Why:** step 2 of the combined plan. Putting "Thetha model twitter" before the transcript (as previous text)
  fixed "tether" in one founder recording (JOURNAL, 21 Oct probe). R-0019 was never trained with prompts, so the list
  could leak into other transcripts. Codex: test with lists that do NOT fit the audio, and on silence.
- **One change vs the live page:** a previous-text prompt. Same model, beam 5, token limit 96.
- **Clips:** the same 100 frozen NCHLT dev clips as R-0022 (read sentences; none contains the list words), plus 5 s of
  silence and 5 s of quiet noise.
- **Lists:** (1) `Thetha model twitter` (the founder's real list), (2) `Ntlakanipho Mgaguli CPUT Bellville WhatsApp`
  (names, chosen by Claude; no isiXhosa sentences invented).
- **Command:** `CT2_USE_MKL=0 .venv/Scripts/python src/decode_audit.py context --clips runs/R-0022/clips.jsonl --out runs/R-0023 --context "Thetha model twitter" --context "Ntlakanipho Mgaguli CPUT Bellville WhatsApp"`
- **Git commit at launch:** 2dff2ea (+ src/decode_audit.py). **Machine:** founder's laptop, $0.
- **Pass rule (set before the run), per list:** at most 1 list word inserted across the 100 clips; WER and CER no more
  than 0.5 points worse than no list; no list word on silence or noise.
- **Already seen on a 3-clip smoke test:** silence and quiet noise with list (1) came out as "thetha" (no list: "i", "c").
  So the silence part will likely fail; the question is how often it leaks into real speech.
