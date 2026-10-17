#!/bin/bash
# R-0009: smoke test for whisper-medium on an NVIDIA L40S (48 GB, g6e.xlarge). Not a real model.
# R-0008 showed medium only fits a 24 GB L4 with gradient checkpointing (~9 s/step). Here: batch 16 x 2 without
# checkpointing (speed + memory), the two-dev-set evaluation (with the same batch set-up this time, P-0007), a medium
# checkpoint save/reload, and medium's scoring speed on FLEURS.
set -euo pipefail
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
bash runs/preflight.sh
aws s3 sync "s3://$BUCKET/datasets/nchlt_xho/extracted/nchlt_xho/" data/nchlt_xho/ --only-show-errors
F=data/fleurs_xh_za
aws s3 sync "s3://$BUCKET/datasets/fleurs_xh_za/" $F/ --only-show-errors
for s in train dev test; do tar xzf $F/audio/$s.tar.gz -C $F/audio/; done
T=data/nchlt_xho/transcriptions
TRAIN="python src/train.py --xml $T/nchlt_xho.trn.xml --root data --fleurs-tsv $F/train.tsv --fleurs-audio $F/audio/train
  --model openai/whisper-medium --language sw --warmup 5 --generation-max-length 96 --batch-size 16 --grad-accum 2"
KEEP="it\]$|train_runtime|peak_gpu|eval_nchlt_cer|eval_fleurs_cer|best_checkpoint|Error|OutOfMemory|Traceback"

echo "=== speed: 30 steps, batch 16 x 2, no checkpointing, no evaluation"
$TRAIN --out /tmp/smoke --max-steps 30 --eval-every 1000 2>&1 | tr '\r' '\n' | grep --line-buffered -E "$KEEP" | grep -vE "^\s*[0-9]+%.*\| *([0-9]|1[0-9]|2[0-4])/30" || true
test -d /tmp/smoke/final || { echo "=== speed test FAILED"; exit 1; }
rm -rf /tmp/smoke

echo "=== two-dev-set check: 4 steps, evaluate NCHLT + FLEURS dev at steps 2 and 4, save, reload"
$TRAIN --out /tmp/smoke2 --max-steps 4 --eval-every 2 --dev-clips 32 \
  --fleurs-dev-tsv $F/dev.tsv --fleurs-dev-audio $F/audio/dev --fleurs-dev-clips 32 2>&1 \
  | tr '\r' '\n' | grep --line-buffered -E "eval_nchlt_cer|eval_fleurs_cer|best_checkpoint|peak_gpu|Error|Traceback"
python -c "from transformers import WhisperForConditionalGeneration as W; W.from_pretrained('/tmp/smoke2/final'); print('medium checkpoint reloads OK')"
du -sh /tmp/smoke2/checkpoints/checkpoint-4
rm -rf /tmp/smoke2

echo "=== scoring speed: stock whisper-medium, sw tag, 200 FLEURS test clips"
python src/baseline.py --fleurs-tsv $F/test.tsv --fleurs-audio $F/audio/test --root data --language sw \
  --model openai/whisper-medium --limit 200 --out out/medium_speed 2>&1 | grep --line-buffered -vE "^\s*$" | tail -2
df -h / | tail -1
