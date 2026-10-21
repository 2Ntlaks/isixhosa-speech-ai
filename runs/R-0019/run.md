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
