#!/bin/bash
# R-0010: second whisper-medium smoke test on the L40S (48 GB). R-0009 ran out of memory at batch 16 x 2 without
# gradient checkpointing. This run tries BOTH remaining set-ups (P-0008), keeps the faster one that fits, and uses it for
# the two-dev-set check, a checkpoint save/reload, and the scoring-speed test.
set -euo pipefail
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
aws s3 sync "s3://$BUCKET/datasets/nchlt_xho/extracted/nchlt_xho/" data/nchlt_xho/ --only-show-errors
F=data/fleurs_xh_za
aws s3 sync "s3://$BUCKET/datasets/fleurs_xh_za/" $F/ --only-show-errors
for s in train dev test; do tar xzf $F/audio/$s.tar.gz -C $F/audio/; done
T=data/nchlt_xho/transcriptions
TRAIN="python src/train.py --xml $T/nchlt_xho.trn.xml --root data --fleurs-tsv $F/train.tsv --fleurs-audio $F/audio/train
  --model openai/whisper-medium --language sw --warmup 5 --generation-max-length 96"

declare -A SECS
try() {  # name, args: 30 steps, no evaluation; records seconds per step if it fits
  echo "=== setup $1: ${*:2}"
  $TRAIN --out /tmp/smoke --max-steps 30 --eval-every 1000 "${@:2}" > /tmp/$1.log 2>&1 || true
  grep -E "peak_gpu|OutOfMemoryError" /tmp/$1.log | cut -c1-200 || true
  if [ -d /tmp/smoke/final ]; then
    SECS[$1]=$(python -c "import re;t=[float(x) for x in re.findall(r\"'train_runtime': ([0-9.]+)\", open('/tmp/$1.log').read())];print(round(t[-1]/30,2))")
    echo "=== setup $1 fits: ${SECS[$1]} s/step (30 steps incl. start-up)"
  else echo "=== setup $1 does not fit"; fi
  rm -rf /tmp/smoke
}
try C --batch-size 16 --grad-accum 2 --gradient-checkpointing
try B --batch-size 8 --grad-accum 4
BEST=""; for k in "${!SECS[@]}"; do [ -z "$BEST" ] || python -c "import sys;sys.exit(0 if ${SECS[$k]} < ${SECS[$BEST]} else 1)" && BEST=$k; done
[ -n "$BEST" ] || { echo "=== no set-up fits"; exit 1; }
case $BEST in C) ARGS="--batch-size 16 --grad-accum 2 --gradient-checkpointing";; B) ARGS="--batch-size 8 --grad-accum 4";; esac
echo "=== chosen: setup $BEST ($ARGS), ${SECS[$BEST]} s/step"

echo "=== two-dev-set check with the chosen set-up: 4 steps, evaluate at 2 and 4, save, reload"
$TRAIN $ARGS --out /tmp/smoke2 --max-steps 4 --eval-every 2 --dev-clips 32 \
  --fleurs-dev-tsv $F/dev.tsv --fleurs-dev-audio $F/audio/dev --fleurs-dev-clips 32 2>&1 \
  | tr '\r' '\n' | grep --line-buffered -E "eval_nchlt_cer|eval_fleurs_cer|best_checkpoint|Error|Traceback"
python -c "from transformers import WhisperForConditionalGeneration as W; W.from_pretrained('/tmp/smoke2/final'); print('medium checkpoint reloads OK')"
du -sh /tmp/smoke2/checkpoints/checkpoint-4
rm -rf /tmp/smoke2

echo "=== scoring speed: stock whisper-medium, sw tag, 200 FLEURS test clips"
python src/baseline.py --fleurs-tsv $F/test.tsv --fleurs-audio $F/audio/test --root data --language sw \
  --model openai/whisper-medium --limit 200 --out out/medium_speed 2>&1 | grep --line-buffered -vE "^\s*$" | tail -2
df -h / | tail -1
