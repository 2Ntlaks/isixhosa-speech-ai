# R-0001 · Stage 1 baseline: stock whisper-small on NCHLT isiXhosa test

- **Why:** the "before" number. Whisper has never been taught isiXhosa; every later run is compared to this.
- **What changes vs previous run:** nothing (first run).
- **Decision:** D-0006 (run stage 1 in the cloud on the full test set; language auto-detected).
- **Command:** `cloud/run_job.sh --run R-0001 --max-hours 1` (node runs `runs/R-0001/job.sh`)
- **Expected:** WER above 80 %; Whisper will label the clips as some other language.

## Outcome
- **Ran:** 2026-10-16, node i-04783cf6e5d0ff258, g6.xlarge on-demand (NVIDIA L4), commit 32e5cbe. Up 17:04:46 UTC,
  packages installed by 17:08:59, transcription 245 s, DONE 17:14:00. Machine time ~9.5 min, about $0.13.
  First launch attempt (spot) found no capacity: P-0003.
- **Result:** WER 196.56 %, CER 75.09 %, exact match 0.79 % (22 clips, all English prompts), 0 empty outputs.
  Details: metrics.json, predictions.jsonl (one line per clip), samples.md.
- **What it means:** Whisper picked 52 different languages (sw 876, yo 392, en 278, sn 258 ...). Swahili-labelled
  clips were closest (CER 40.3 %). 30 % of outputs not in Latin script; ~19 % stuck in repetition loops.
  It wrote 15 328 words for 8 107 reference words (word splitting -> WER > 100 %). On Latin-script outputs it
  almost never writes kh (9/311), dl (4/99), hl (13/199); th 83/532, x 30/186.
- **Library warnings (harmless here):** transformers warned about `attention_mask` not set (Whisper's encoder input is
  always padded to 30 s, so no mask is needed) and about `forced_decoder_ids` being ignored in favour of task=transcribe.
- **Results page:** evidence/stage1-baseline.html (published as a private Claude artifact).
- **Audio for the founder's listening check:** 20 sample clips copied to data/listen/R-0001/ (gitignored).
