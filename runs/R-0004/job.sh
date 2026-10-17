#!/bin/bash
# R-0003 + R-0004 on one GPU node (saves a second boot and data download).
#   R-0003: stock whisper-small with the <|sw|> tag forced, no training (fair baseline for stage 2).
#   R-0004: first real fine-tune, 4000 steps on the NCHLT training split, then scored on the full test set.
set -euo pipefail
bash runs/preflight.sh
aws s3 sync "s3://$BUCKET/datasets/nchlt_xho/extracted/nchlt_xho/" data/nchlt_xho/ --only-show-errors
echo "audio: $(find data/nchlt_xho/audio -name '*.wav' | wc -l) wav files"
T=data/nchlt_xho/transcriptions
EVAL="python src/baseline.py --xml $T/nchlt_xho.tst.xml --train-xml $T/nchlt_xho.trn.xml --root data --language sw"

echo "=== R-0003: stock whisper-small, <|sw|> forced, full test set"
$EVAL --model openai/whisper-small --out out/R-0003 2>&1 | grep -vE "^\s*$" | tee out/R-0003.log
aws s3 sync out/R-0003 "s3://$BUCKET/jobs/R-0003/out/" --only-show-errors

echo "=== R-0004: fine-tune 4000 steps"
python src/train.py --xml $T/nchlt_xho.trn.xml --root data --out out/model --language sw \
  --max-steps 4000 --eval-every 500 --dev-clips 600 2>&1 | grep -vE "^\s*$" | tee out/train.log
aws s3 sync out/model/final "s3://$BUCKET/models/R-0004/" --only-show-errors   # kept (models/ never expires)

echo "=== R-0004: score the best checkpoint on the full test set"
$EVAL --model out/model/final --out out/eval 2>&1 | grep -vE "^\s*$" | tee out/eval.log
