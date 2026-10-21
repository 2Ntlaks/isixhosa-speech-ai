# R-0019 · Stage 3, more data, step 1: whisper-medium on NCHLT + FLEURS + Swivuriso

- **Why:** Thetha learned from ~64 h of mostly read speech (NCHLT + FLEURS). Swivuriso (South Africa African Next
  Voices, CC BY 4.0, D-0024) adds read AND unscripted isiXhosa from 407 new speakers on phones and headsets.
- **One change vs R-0012:** Swivuriso train added. Same model (whisper-medium), same NCHLT/FLEURS data, same 6 dev
  speakers, 4000 steps x 32 clips, lr 1e-5, warmup 500, linear decay, bf16, best checkpoint on NCHLT dev CER.
- **Data rules (decided by the agent, logged here):** only clips of 1-30 s (Whisper hears 30 s at most; 235 of 427 h
  are in longer clips and need cutting first, a later step); clips with [?] dropped (the transcriber could not make
  out a stretch, so the text is missing words); [um]/[cs]/[pause] tags removed, the words kept; text cleaned with the
  scoring rules; any clip whose sentence appears in a test or dev set is dropped; transcripts over 440 tokens dropped.
  Expected from the transcript files: ~161 h of Swivuriso train kept (~2.5x the current 64 h).
- **Note on steps:** 4000 steps x 32 = 128 000 clip views for ~84 000 clips, so each clip is seen ~1.5 times (R-0012:
  ~2.8 times). Kept at 4000 so the only change is the data; a longer run is a separate experiment if this one helps.
- **New test set:** Swivuriso dev_test (own speakers, same clip rules), scored for R-0012 (as R-0018) and R-0019.
- **Command:** `DISK_GB=250 FALLBACK_TYPES="" cloud/run_job.sh --run R-0019 --type g6e.xlarge --market ondemand --max-hours 6`
- **Founder approval:** 2026-10-21, "Launch medium (Recommended)" in reply to ~4.5 h / ~$8-9 / cap 6 h (D-0024, D-0025).
- **Expected:** Swivuriso test clearly better than R-0018; FLEURS and NCHLT test not worse than R-0012 (8.03 / 2.33 CER).
  Est. ~4.5 h, ~$8-9, cap 6 h (~$11).

## Outcome · 2026-10-21 · started (commit 6a71856, node i-0d13aae1c15e11850, g6e.xlarge on-demand)
- Launch: no L40S capacity 08:44-09:08 SAST; retry loop got one at 09:08 SAST (07:08 UTC). Cap 6 h.
- Finished 10:06 UTC (12:06 SAST), DONE. Node 07:09-10:06 UTC, ~2.97 h at $1.861/h = ~$5.53 (estimate ~4.5 h / ~$8).
- Swivuriso prep (summary in swivuriso_summary.json): train 62 786 clips -> 38 536 kept / 160.96 h (19 005 over 30 s,
  5 244 with [?], 1 empty, 0 unreadable); dev_test -> 2 145 clips / 9.40 h / 24 speakers. ~31 min on 4 CPUs.
  Prepared copy cached in S3 datasets/swivuriso_xho_16k/.
- Leak filter dropped 6 139 Swivuriso train clips whose sentence is in a test/dev set (scripted prompts repeat across
  speakers); 0 transcripts over 440 tokens. Training data: 78 100 clips, 210.82 h, 603 speakers (R-0012: 64.23 h).
- Memory check passed at batch 8 (no fallback); peak 34.58 GB of 48. Training 7 402 s (1.85 s/step incl. evaluations).
- Dev CER (NCHLT, same 600 clips): best at step 4000, 2.91, still falling at the end (R-0012: 2.66). Expected: NCHLT
  clips are now seen ~1.5x instead of ~2.8x.
- **Swivuriso test (2145 clips, own speakers): WER 19.12 %, CER 4.12 %** (R-0018 = R-0012: 37.32 / 9.00).
  Read 19.2 / 4.1 (R-0012 33.4 / 7.6); **unscripted 19.0 / 4.1 (R-0012 42.4 / 10.8)**. Exact clips 20.6 % (6.3 %).
- **FLEURS test (1034 clips, never trained on): WER 30.32 %, CER 6.24 %** (R-0012: 37.83 / 8.03).
- **NCHLT test (2770 clips): WER 13.67 %, CER 2.31 %** (R-0012: 12.71 / 2.33). Seen sentences slightly worse
  (10.7 / 1.8 vs 9.0 / 1.7), unseen sentences better (26.6 / 4.4 vs 28.7 / 5.0).
- Conclusion: more and more varied speech helped where it matters. Natural speech: letter errors cut by ~60 %. FLEURS,
  a dataset it never trained on: ~22 % fewer letter errors. NCHLT: same letters, slightly more word slips on sentences
  it had memorised, fewer on new sentences. Caveat: the Swivuriso test comes from the same project (same app, topics)
  as its training data, so part of that gain is "home ground"; FLEURS is the fairest outside check.
- Model: s3://mgaguli-studio-render-188250416608/models/R-0019/ (3.06 GB).
