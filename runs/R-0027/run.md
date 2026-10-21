# R-0027 · Swivuriso long clips cut into pieces + whisper-small with all usable Swivuriso (for the browser demo)

- **Why:** the founder wants Thetha improved with more Swivuriso data and the free in-browser demo upgraded (it still
  runs R-0007, whisper-small without Swivuriso). R-0019 used only Swivuriso clips of 1-30 s. The 19,005 train clips over
  30 s (mostly people talking freely) were skipped because Whisper hears at most 30 s; relaxed speech is the weak spot
  (R-0024). D-0024/D-0026 cover the spend (AWS credits, up to $5/h, past the $30 brake).
- **New code:** `src/swivuriso_long.py` (extract long train clips; forced alignment with torchaudio MMS_FA; cut at the
  widest pause before 28 s; per-piece alignment scores), `runs/R-0027/gate.py` (quality gate), `runs/R-0027/job.sh`.
  Checked first on the laptop with joined NCHLT test clips where every word's true place is known
  (`runs/R-0027/check_cutter.py` -> `check_cutter.json`).
- **Data rules (unchanged from R-0019):** train split only (dev/test speakers never touched); clips with [?] dropped;
  text = scoring.normalise. New: a long clip whose text contains any test/dev sentence of 3+ words is dropped whole.
- **Quality gate (before any training):** R-0019 (never trained on these clips) transcribes 600 random pieces. Pieces
  are split into 5 bands by their weakest word's alignment score; the threshold is the lowest band from which every
  band up has CER <= 8 %. Stop if the kept sample's CER > 8 % or < 20 h are kept.
- **Model:** whisper-small, R-0007's recipe (4000 steps, batch 16 x 2, lr 1e-5, warm-up 500), data = NCHLT + FLEURS
  (as R-0007) + Swivuriso short clips (as R-0019) + the kept pieces. Two data changes vs R-0007 (short and long
  Swivuriso), on purpose: this is the demo model; the effect of the pieces alone is measured with the medium model next.
- **Before:** R-0007 on Swivuriso test (never measured) runs on the same node.
- **Ship rule for the demo:** better than R-0007 on FLEURS test and Swivuriso test, NCHLT test CER not worse by more
  than 0.5. Then ONNX conversion and a browser check on the laptop; publishing waits for the founder's OK.
- **Command:** `DISK_GB=300 FALLBACK_TYPES="" cloud/run_job.sh --run R-0027 --type g6e.xlarge --market ondemand --max-hours 5`
- **Cost estimate:** ~2.5-3.5 h x $1.861 = ~$5-7. October GPU spend before: ~$23 (brake $30, may be passed, D-0026).

## Laptop check of the cutter · 2026-10-21 23:15 SAST · PASSED ($0)
`check_cutter.json`: 8 "long clips" of ~1 min, each 14 NCHLT test clips of one speaker joined (true word places known).
- 25 pieces of 2.7-27.0 s (median 17.1 s): all within the 28 s limit.
- **328 / 328 words** fall in a piece whose audio overlaps their own source clip (no word lands in the wrong piece).
- R-0019-int8 on the pieces: WER 18.9 / CER 2.71 (its NCHLT test score is 13.67 / 2.31; pieces are longer and have more
  words to get wrong at the joins). First word right in 21/25 pieces, last word in 21/25.
- Alignment scores on clean read speech: weakest word median 0.80, mean median 0.94 (a reference for the gate).

## Launch note · 2026-10-21 23:30 SAST
- No g6e.xlarge (L40S) on-demand capacity in us-east-1 on 6 tries (23:14-23:26). whisper-small and the aligner fit a
  24 GB GPU, so the run moves to **g6.xlarge (L4 24 GB, 16 GB RAM, $0.805/h)**, falling back to g5.xlarge (A10G,
  $1.006/h). Extraction workers 6 -> 4 to fit 16 GB of RAM. Cap 6 h (slower GPU). Estimate ~4-5 h x $0.805 = ~$3.5-4.
- **Command:** `DISK_GB=300 FALLBACK_TYPES="g5.xlarge" cloud/run_job.sh --run R-0027 --type g6.xlarge --market ondemand --max-hours 6`
