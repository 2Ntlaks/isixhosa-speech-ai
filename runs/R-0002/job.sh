#!/bin/bash
# R-0002: smoke test of the stage 2 training pipeline (not a real model). Runs on the GPU node.
set -euo pipefail
aws s3 sync "s3://$BUCKET/datasets/nchlt_xho/extracted/nchlt_xho/" data/nchlt_xho/ --only-show-errors
echo "audio: $(find data/nchlt_xho/audio -name '*.wav' | wc -l) wav files, $(du -sh data | cut -f1)"
T=data/nchlt_xho/transcriptions
TRAIN="python src/train.py --xml $T/nchlt_xho.trn.xml --root data --out out/model --language sw --eval-every 20 --dev-clips 64 --warmup 5"
echo "=== part 1: train 20 steps, save a checkpoint"
$TRAIN --max-steps 20 2>&1 | grep -vE "^\s*$" | tee out/train_part1.log
echo "=== part 2: resume from that checkpoint and continue to 40 steps"
$TRAIN --max-steps 40 2>&1 | grep -vE "^\s*$" | tee out/train_part2.log
echo "=== part 3: score the 40-step model on 300 test clips"
python src/baseline.py --xml $T/nchlt_xho.tst.xml --train-xml $T/nchlt_xho.trn.xml --root data --out out/eval \
  --model out/model/final --language sw --limit 300 2>&1 | grep -vE "^\s*$" | tee out/eval.log
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
