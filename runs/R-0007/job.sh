#!/bin/bash
# R-0005 + R-0006 + R-0007 on one GPU node (one boot, one data download).
#   R-0005: R-0004's model (NCHLT only) scored on the FLEURS isiXhosa test set: how it copes with long natural sentences.
#   R-0006: stock whisper-small with <|sw|> forced, scored on FLEURS test: the fair FLEURS baseline.
#   R-0007: same recipe as R-0004 with one change, FLEURS train added to the training data; scored on NCHLT and FLEURS test.
set -euo pipefail
bash runs/preflight.sh
aws s3 sync "s3://$BUCKET/datasets/nchlt_xho/extracted/nchlt_xho/" data/nchlt_xho/ --only-show-errors
F=data/fleurs_xh_za
aws s3 sync "s3://$BUCKET/datasets/fleurs_xh_za/" $F/ --only-show-errors
for s in train test; do tar xzf $F/audio/$s.tar.gz -C $F/audio/; done
python - <<'PY'
import sys; sys.path.insert(0, "src")
import os, soundfile as sf, fleurs
for s in ("train", "test"):
    c = fleurs.load_split(f"data/fleurs_xh_za/{s}.tsv", f"data/fleurs_xh_za/audio/{s}")
    missing = [x["path"] for x in c if not os.path.exists(x["path"])]
    assert not missing, f"{len(missing)} FLEURS {s} files missing, e.g. {missing[:2]}"
    assert sf.info(c[0]["path"]).samplerate == 16000
    print(f"FLEURS {s}: {len(c)} clips, all audio present, 16 kHz")
PY
echo "audio: $(find data -name '*.wav' | wc -l) wav files"
aws s3 sync "s3://$BUCKET/models/R-0004/" models/R-0004/ --only-show-errors
echo "=== preflight 2: 2 training steps on NCHLT + FLEURS (exercises the new FLEURS training path)"
python src/train.py --xml data/nchlt_xho/transcriptions/nchlt_xho.trn.xml --root data --fleurs-tsv $F/train.tsv \
  --fleurs-audio $F/audio/train --out /tmp/preflight2 --max-steps 2 --eval-every 2 --dev-clips 16 --warmup 1 \
  --generation-max-length 96 2>&1 | grep --line-buffered -E "fleurs_train_clips|best_dev_cer|Error|Traceback"
rm -rf /tmp/preflight2

T=data/nchlt_xho/transcriptions
SEEN="--train-xml $T/nchlt_xho.trn.xml --train-fleurs-tsv $F/train.tsv"
EVAL="python src/baseline.py --root data --language sw $SEEN"
FTEST="--fleurs-tsv $F/test.tsv --fleurs-audio $F/audio/test"
keep() { aws s3 sync "out/$1" "s3://$BUCKET/jobs/$1/out/" --only-show-errors; }

echo "=== R-0005: R-0004 model on FLEURS test"
$EVAL $FTEST --model models/R-0004 --out out/R-0005 2>&1 | grep --line-buffered -vE "^\s*$" | tee out/R-0005.log
keep R-0005
echo "=== R-0006: stock whisper-small, <|sw|> forced, on FLEURS test"
$EVAL $FTEST --model openai/whisper-small --out out/R-0006 2>&1 | grep --line-buffered -vE "^\s*$" | tee out/R-0006.log
keep R-0006

echo "=== R-0007: fine-tune 4000 steps on NCHLT + FLEURS train"
python src/train.py --xml $T/nchlt_xho.trn.xml --root data --fleurs-tsv $F/train.tsv --fleurs-audio $F/audio/train \
  --out out/model --language sw --max-steps 4000 --eval-every 500 --dev-clips 600 --generation-max-length 96 2>&1 \
  | grep --line-buffered -vE "^\s*$" | tee out/train.log
aws s3 sync out/model/final "s3://$BUCKET/models/R-0007/" --only-show-errors   # kept (models/ never expires)

echo "=== R-0007: score on NCHLT test"
$EVAL --xml $T/nchlt_xho.tst.xml --max-new-tokens 96 --model out/model/final --out out/eval_nchlt 2>&1 | grep --line-buffered -vE "^\s*$" | tee out/eval_nchlt.log
echo "=== R-0007: score on FLEURS test"
$EVAL $FTEST --model out/model/final --out out/eval_fleurs 2>&1 | grep --line-buffered -vE "^\s*$" | tee out/eval_fleurs.log
