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

## Outcome · 2026-10-21 21:10 SAST · FAILED the pass rule (laptop, $0)
| List (previous text) | WER % | CER % | list words inserted (100 clips) | 5 s silence | 5 s quiet noise |
|---|---|---|---|---|---|
| none | 30.38 | 4.43 | - | "i" | "c" |
| Thetha model twitter | 31.74 | 4.47 | **0** | "thetha" | "thetha" |
| Ntlakanipho Mgaguli CPUT Bellville WhatsApp | 32.08 | 4.40 | **0** | "Ntlakanipho" | "Ntlakanipho" |
- Unseen sentences (82): none 34.29 / 4.67; list 1 36.33 / 4.79; list 2 36.33 / 4.75. Time: no difference.
- **Good:** no list word leaked into real speech (0 of 100 clips, both lists); letters (CER) about unchanged.
- **Bad 1:** WER +1.4 and +1.7 points (rule: at most +0.5). Lists changed 6 and 10 clips, mostly word splits and
  double vowels ("yayizakuba" -> "yayiza kuba", "zepolisi" -> "zeepolisi"); some changes fixed, some broke words.
- **Bad 2:** on silence and noise the model writes a list word, so a list must never be used on audio without speech.
- **Reading:** a list can fix a name (the "Thetha" probe) without spraying names into other speech, but it nudges word
  splitting on everything. Not safe as an always-on setting. Usable only as an opt-in "my words" pass that is shown next
  to the normal transcript (with and without), and only on recordings with speech. The real fix is training with prompts
  (combined plan, later list), so the model learns lists are hints.
