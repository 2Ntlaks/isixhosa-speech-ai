#!/bin/bash
# R-0008: smoke test for whisper-medium (769M parameters) on one L4 (24 GB). Not a real model.
# Measures, for 3 memory set-ups, whether training fits and how many seconds a step takes; then tests the new
# two-dev-set evaluation (NCHLT picks the best checkpoint, FLEURS dev is information only) and medium's scoring speed.
set -euo pipefail
bash runs/preflight.sh
aws s3 sync "s3://$BUCKET/datasets/nchlt_xho/extracted/nchlt_xho/" data/nchlt_xho/ --only-show-errors
F=data/fleurs_xh_za
aws s3 sync "s3://$BUCKET/datasets/fleurs_xh_za/" $F/ --only-show-errors
for s in train dev test; do tar xzf $F/audio/$s.tar.gz -C $F/audio/; done
T=data/nchlt_xho/transcriptions
TRAIN="python src/train.py --xml $T/nchlt_xho.trn.xml --root data --fleurs-tsv $F/train.tsv --fleurs-audio $F/audio/train
  --model openai/whisper-medium --language sw --warmup 5 --generation-max-length 96"
KEEP="train_runtime|peak_gpu|fleurs_train_clips|eval_nchlt_cer|eval_fleurs_cer|Error|error|OutOfMemory|Traceback"

try() {  # name, extra args: 20 steps, no evaluation, so the time is pure training
  echo "=== setup $1"
  { $TRAIN --out /tmp/smoke --max-steps 20 --eval-every 1000 "${@:2}" 2>&1 | grep --line-buffered -E "$KEEP"; } \
    || echo "=== setup $1 FAILED (probably out of GPU memory)"
  rm -rf /tmp/smoke
}
try "A: batch 16 x 2, no checkpointing" --batch-size 16 --grad-accum 2
try "B: batch 8 x 4, no checkpointing" --batch-size 8 --grad-accum 4
try "C: batch 16 x 2, gradient checkpointing" --batch-size 16 --grad-accum 2 --gradient-checkpointing

echo "=== two-dev-set check: 4 steps, evaluate NCHLT + FLEURS dev at step 2 and 4, save, reload"
$TRAIN --out /tmp/smoke2 --max-steps 4 --eval-every 2 --batch-size 8 --grad-accum 4 --dev-clips 32 \
  --fleurs-dev-tsv $F/dev.tsv --fleurs-dev-audio $F/audio/dev --fleurs-dev-clips 32 2>&1 \
  | grep --line-buffered -E "$KEEP|best_checkpoint"
python -c "from transformers import WhisperForConditionalGeneration as W; W.from_pretrained('/tmp/smoke2/final'); print('medium checkpoint reloads OK')"
du -sh /tmp/smoke2/checkpoints/* | tail -1
rm -rf /tmp/smoke2

echo "=== scoring speed: stock whisper-medium, sw tag, 200 FLEURS test clips"
python src/baseline.py --fleurs-tsv $F/test.tsv --fleurs-audio $F/audio/test --root data --language sw \
  --model openai/whisper-medium --limit 200 --out out/medium_speed 2>&1 | grep --line-buffered -vE "^\s*$" | tail -3
df -h / | tail -1
