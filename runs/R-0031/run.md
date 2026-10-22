# R-0031 · R-0029's fast int8 copy, checked in the cloud (laptop memory is short)

- **Why:** R-0029 (medium + long-clip pieces) narrowly failed its ship rule (Swivuriso CER 4.14 vs 4.12, one runaway
  output) but improved unscripted speech (4.1 -> 3.6). The founder wants it tried for real in the Siyamthanda hub, which
  runs the int8 copy on CPU. The laptop ran out of memory downloading the full model (13:43), so the founder OK'd doing
  the conversion and the tests on a small AWS machine (under $1) and bringing back only the int8 copy.
- **What:** (1) R-0029 and R-0019 -> CTranslate2 int8 (as R-0020) plus tokenizer.json (faster-whisper needs it), saved to
  S3 models/R-0029-int8/ and models/R-0019-int8/. (2) R-0020-style check of R-0029-int8 against its GPU outputs, 200
  unseen-sentence NCHLT test clips (`src/eval_ct2.py`, seed 1). (3) Soapies test exactly as R-0030 (391 clips, --lang
  sw, greedy, 96 tokens) on R-0029-int8 and R-0019-int8 on the same machine, so the two are compared like for like.
- **Pass:** int8 check: CER within 0.3 of the GPU on the same clips (as R-0020). Soapies: reported, no rule (R-0019's
  node score should match its laptop 29.29 closely; any gap is the CPU type).
- **Command:** `FALLBACK_TYPES="c7i.4xlarge c6i.8xlarge" cloud/run_job.sh --run R-0031 --type c7i.8xlarge --market spot --max-hours 2`
  (CPU node with the same GPU image; nvidia-smi fails harmlessly). 32 vCPU, spot ~ $0.5-0.6/h, about 1 h.
- Soapies predictions stay local (gitignored, D-0016); only scores go in git.
- **Attempt 1 (13:53-13:57 SAST) failed:** int8 folders lacked preprocessor_config.json and the tokenizer files (P-0020).
  Job fixed to copy them; relaunched.

## Outcome (2026-10-22, 14:19 SAST): int8 copy PASSED; on mixed speech R-0029 beats R-0019

- **Node:** c7i.8xlarge spot (32 vCPU), 13:59-14:19 SAST, ~20 min at ~$0.63-0.73/h; with attempt 1 **~$0.30** in all.
- **int8 copies:** S3 models/R-0029-int8/ and models/R-0019-int8/, 744 MB each, with processor/tokenizer files and
  tokenizer.json (ready for faster-whisper).
- **int8 check (NCHLT test, 200 unseen-sentence clips, greedy):** int8 CPU WER 27.82 / CER 4.71 vs the same model on GPU
  26.62 / 4.53; 181/200 outputs identical. CER gap 0.18 <= 0.3: **PASSED** (R-0020 for R-0019: gap 0.06, 184/200).
- **Soapies (391 clips, R-0030 settings, same node):**

| Model | CER % | WER % | English words heard | isiXhosa words heard |
|---|---|---|---|---|
| R-0019-int8 (current medium) | 29.56 | 66.92 | 48.7 % | 27.4 % |
| **R-0029-int8 (new medium)** | **28.14** | **64.32** | **51.0 %** | **30.2 %** |

  R-0019 on the laptop (R-0030) was 29.29 / 66.62: the node's CPU shifts results by ~0.3, so only same-node numbers
  are compared. No runaway outputs in either model here (none longer than 1.5x the reference; the 96-token limit caps
  them anyway). 2.47 s per clip each with 10 threads.
- **What it means:** on the speech closest to real use (mixed, unscripted), R-0029 is a little better than R-0019:
  1.4 fewer letter errors in 100, more of both languages' words heard. With R-0029's Swivuriso unscripted gain (4.1 ->
  3.6) this supports trying it in the Siyamthanda test next to R-0019; the ship rule's failure (R-0029) stands, so it
  does not replace R-0019 anywhere without the founder's decision.
