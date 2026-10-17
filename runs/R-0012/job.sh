#!/bin/bash
# R-0011 + R-0012 on one GPU node (L40S 48 GB, g6e.xlarge).
#   R-0011: stock whisper-medium with <|sw|> forced, scored on NCHLT test and FLEURS test: the fair medium baseline.
#   R-0012: R-0007's recipe with ONE change, whisper-medium instead of whisper-small; scored on NCHLT and FLEURS test.
#   Set-up from R-0010: batch 8 x grad-accum 4 = 32 clips per step (same as R-0007), no gradient checkpointing.
#   FLEURS dev (200 clips) is scored at each evaluation for information only; the checkpoint is still chosen on NCHLT dev.
# Checkpoints (8.6 GB each) are written to model/, outside out/, so the 5-minute S3 sync does not copy them; only the
# final model goes to S3 (models/R-0012/), plus log_history.json and data_split.json into out/model/.
set -euo pipefail
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
aws s3 sync "s3://$BUCKET/datasets/nchlt_xho/extracted/nchlt_xho/" data/nchlt_xho/ --only-show-errors
F=data/fleurs_xh_za
aws s3 sync "s3://$BUCKET/datasets/fleurs_xh_za/" $F/ --only-show-errors
for s in train dev test; do tar xzf $F/audio/$s.tar.gz -C $F/audio/; done
echo "audio: $(find data -name '*.wav' | wc -l) wav files"; df -h / | tail -1

T=data/nchlt_xho/transcriptions
SEEN="--train-xml $T/nchlt_xho.trn.xml --train-fleurs-tsv $F/train.tsv"
EVAL="python src/baseline.py --root data --language sw $SEEN"
NTEST="--xml $T/nchlt_xho.tst.xml --max-new-tokens 96"
FTEST="--fleurs-tsv $F/test.tsv --fleurs-audio $F/audio/test"
mkdir -p out/R-0011
keep() { aws s3 sync "out/$1" "s3://$BUCKET/jobs/$1/out/" --only-show-errors; }
quiet() { grep --line-buffered -vE "^\s*$"; }

echo "=== R-0011: stock whisper-medium, <|sw|> forced, on NCHLT test"
$EVAL $NTEST --model openai/whisper-medium --out out/R-0011/eval_nchlt 2>&1 | quiet | tee out/R-0011/eval_nchlt.log \
  || echo "=== R-0011 NCHLT FAILED (training continues)"
echo "=== R-0011: stock whisper-medium, <|sw|> forced, on FLEURS test"
$EVAL $FTEST --model openai/whisper-medium --out out/R-0011/eval_fleurs 2>&1 | quiet | tee out/R-0011/eval_fleurs.log \
  || echo "=== R-0011 FLEURS FAILED (training continues)"
keep R-0011 || true

echo "=== R-0012: fine-tune whisper-medium 4000 steps on NCHLT + FLEURS train"
mkdir -p out/model
python src/train.py --xml $T/nchlt_xho.trn.xml --root data --fleurs-tsv $F/train.tsv --fleurs-audio $F/audio/train \
  --fleurs-dev-tsv $F/dev.tsv --fleurs-dev-audio $F/audio/dev --fleurs-dev-clips 200 \
  --model openai/whisper-medium --batch-size 8 --grad-accum 4 \
  --out model --language sw --max-steps 4000 --eval-every 500 --dev-clips 600 --generation-max-length 96 2>&1 \
  | quiet | tee out/train.log
cp model/log_history.json model/data_split.json out/model/
aws s3 sync model/final "s3://$BUCKET/models/R-0012/" --only-show-errors   # kept (models/ never expires)

echo "=== R-0012: score on NCHLT test"
$EVAL $NTEST --model model/final --out out/eval_nchlt 2>&1 | quiet | tee out/eval_nchlt.log
echo "=== R-0012: score on FLEURS test"
$EVAL $FTEST --model model/final --out out/eval_fleurs 2>&1 | quiet | tee out/eval_fleurs.log
