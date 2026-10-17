# R-0002 · Stage 2 smoke test: does the training pipeline work end to end?

- **Why:** before paying for 2-3 GPU hours, prove every part works on a tiny run: data download, training, checkpoint,
  resume after a restart, saving the final model, scoring it. Also measures seconds per step, so the full run's
  time and cost can be estimated from a real number instead of a guess. Also checks remote access (P-0002 fix).
- **Not a real model:** 40 steps is far too short to learn isiXhosa; its scores are not comparable to anything.
- **Command:** `cloud/run_job.sh --run R-0002 --max-hours 1 --market ondemand`
- **Expected:** both training parts finish, part 2 says "resuming from .../checkpoint-20", eval writes metrics.json.

## Attempt 1 · 2026-10-17 06:53 UTC · FAILED (commit a922e19)
- Data download fine (46 651 wav, 6.2 GB, ~6 min); split fine (42 269 train clips, 51.2 h, 195 speakers;
  dev speakers 005 023 066 077 173 192; 6 clips over 30 s dropped). Training crashed immediately:
  `ImportError: Using the Trainer with PyTorch requires accelerate>=0.26.0` (P-0005).
- Machine time ~8 min, about $0.11.
- Fix: accelerate==1.1.1 added to requirements-gpu.txt; new runs/preflight.sh (2 training steps on 4 speakers
  before the full download) so this class of error costs ~3 min instead of ~8.

## Attempt 2 · 2026-10-17 07:12 UTC · DONE (commit 08971f3)
- Preflight OK (2 steps on 4 speakers, saved and reloaded) about 3 min after boot. Full data sync ~6 min.
- Part 1: 20 steps from the stock model, checkpoint-20 saved. Part 2: "resuming from out/model/checkpoints/checkpoint-20",
  continued to 40 steps. Resume works.
- **Speed: 1.65 s per step** (32 clips per step) on the L4, steady. Batch 16 x 2 fits in memory.
- Dev CER (64 clips): 20.2 % after 20 steps, 18.3 % after 40. Test, first 300 clips (all speaker 500):
  WER 77.5 %, CER 16.8 % (R-0001 on the same speaker: WER 161.7 %, CER 60.0 %).
- **Surprise:** the 2-step preflight model already scored dev CER 25.8 % (16 clips). That much improvement can't come
  from 2 tiny training steps, so most of the jump must come from *forcing the <|sw|> tag* (no wrong-language or
  wrong-script guesses), not from learning. Follow-up: R-0003 scores the stock model with the tag forced, so stage 2's
  real gain is measured against a fair baseline.
- Harmless messages: "missing keys ['proj_out.weight']" (output layer shares weights with the input embeddings, so it
  isn't stored separately); torch.load / tokenizer deprecation warnings.
- Machine time ~12 min, about $0.16. Checkpoints and smoke model in S3 under jobs/R-0002/out/model/ (expire in 30 days).
