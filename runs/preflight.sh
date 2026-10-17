#!/bin/bash
# Shared preflight for training jobs: download 4 speakers (~1 min), train 2 steps, save, reload.
# Catches missing packages, API mistakes and GPU problems ~3 minutes after boot, before the full 6-minute
# data download and hours of training. Called at the top of runs/R-xxxx/job.sh.
set -euo pipefail
D="s3://$BUCKET/datasets/nchlt_xho/extracted/nchlt_xho"
aws s3 sync "$D/transcriptions/" data/nchlt_xho/transcriptions/ --only-show-errors
for s in 001 002 003 006; do   # 2 women, 2 men from the training split
  aws s3 sync "$D/audio/$s/" "data/nchlt_xho/audio/$s/" --only-show-errors
done
echo "=== preflight: 2 training steps on 4 speakers"
python src/train.py --xml data/nchlt_xho/transcriptions/nchlt_xho.trn.xml --root data --out /tmp/preflight \
  --only-existing --dev-speakers 2 --dev-clips 16 --max-steps 2 --eval-every 2 --warmup 1 2>&1 | grep --line-buffered -vE "^\s*$" | tail -5
python -c "from transformers import WhisperForConditionalGeneration as W; W.from_pretrained('/tmp/preflight/final'); print('preflight OK: trained, saved and reloaded')"
rm -rf /tmp/preflight
