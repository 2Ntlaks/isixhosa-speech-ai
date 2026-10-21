# Thetha: combined plan (Claude + Codex, 2026-10-21)

Drawing: `docs/thetha-plan.png`. Sources: `docs/claude-ideas-2026-10-21.md`, `docs/codex-ideas-2026-10-21.md`, R-0021.

## Done the same day

- Beam 5 is the live default for int8 models (R-0021: CER 5.01 -> 4.73, 14 clips better, 9 worse, no slowdown).
- `live.py --public` no longer prints transcripts to the server log (Codex finding).
- Output-cap audit (Codex asked for it): on all 2,145 Swivuriso test clips, R-0019's longest reference is 172 tokens and its
  longest output is 168; the densest clip scales to ~194 tokens per 30 s. The live 225-token cap is not cutting anything
  off. The "amanye" error was a short phrase, so neither the cap nor the 30 s cut can explain it.

## Where we agree

- Keep beam 5. Never do a blind "tether -> Thetha" replacement. Never suppress English words.
- Word lists ("my words") only per recording, with undo, after a harm check.
- Founder corrections are the most valuable test data we have.

## Where Codex changed the plan (Claude accepts all four)

1. **Do not assume fast speech is fixed by more fast speech.** First find out why "amanye" happens. Compare the phrase with
   its surrounding audio, cut short, and slowed to 0.9x. Before the cutter, measure how fast the long Swivuriso clips really are.
2. **The harm check must use wrong word lists, not only empty ones.** An empty prompt cannot show harm from a list that
   doesn't fit the recording. Also test on silence.
3. **Test the five guesses first.** Both "pick another word" and Claude's word-list rescoring only help if the right
   word is already among beam 5's candidates. One audit answers both questions.
4. **Translation waits** until correcting transcripts is shown to be worth it.

## Order

| # | Step | Cost | Pass rule |
|---|---|---|---|
| 1 | Five-candidate audit: 100 NCHLT dev clips + ~20 new founder clips, frozen before outputs are seen; only `num_hypotheses` 1 -> 5 | free, laptop, < 1 h | best-of-5 WER >= 3 points better than top choice; top choice not worse; time <= 1.25x |
| 2 | "My words" harm check: relevant lists, wrong lists, silence | free, laptop | target words recovered, no false insertions |
| 3 | Fast-speech diagnosis (context / crop / 0.9x; speaking rate of long clips) | free, laptop | tells whether step 4 or the cutter is the right fix |
| 4 | Paired 500-step continuation from R-0019: control vs unscripted Swivuriso sampled 2x | ~$3-8, founder OK first | candidate beats control on unscripted dev with NCHLT/FLEURS not worse |
| later | Long-clip cutter (small pilot, listen to rejected pieces too), prompt-robust training, translation line | | |

## Needed from the founder

About 20 everyday sentences recorded in Thetha, each with what he really said typed in (via the correct box). Also the
endings of the school and "shackles" sentences.
