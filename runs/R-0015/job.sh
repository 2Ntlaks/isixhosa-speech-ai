#!/bin/bash
# R-0015 + R-0016 on one GPU node (L40S 48 GB, g6e.xlarge): stage 4, teaching R-0012 to keep English words in English.
#   Both continue from R-0012 (not from stock medium), 2000 steps, lr 5e-6, same NCHLT + FLEURS data as R-0012, plus:
#   R-0015: + 10 h NCHLT English, learned with Whisper's own <|en|> tag.
#   R-0016: R-0015's data + 8000 stitched isiXhosa+English clips (real clips joined, <|sw|> tag). One change vs R-0015.
#   Best checkpoint chosen on the Soapies dev set (38 speakers, never trained on, D-0016); NCHLT and FLEURS dev are
#   scored for information. After training: NCHLT test and FLEURS test here (did isiXhosa get worse?), and an int8
#   copy for the laptop, where the Soapies test is scored with the same engine as R-0014.
set -euo pipefail
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
aws s3 sync "s3://$BUCKET/datasets/nchlt_xho/extracted/nchlt_xho/" data/nchlt_xho/ --only-show-errors
aws s3 sync "s3://$BUCKET/datasets/nchlt_eng/extracted/nchlt_eng/" data/nchlt_eng/ --only-show-errors
aws s3 sync "s3://$BUCKET/datasets/soapies_engxho/" data/soapies_engxho/ --only-show-errors --exclude "*.zip"
F=data/fleurs_xh_za
aws s3 sync "s3://$BUCKET/datasets/fleurs_xh_za/" $F/ --only-show-errors
for s in train dev test; do tar xzf $F/audio/$s.tar.gz -C $F/audio/; done
aws s3 sync "s3://$BUCKET/models/R-0012/" init/R-0012/ --only-show-errors
echo "audio: $(find data -name '*.wav' | wc -l) wav files"; df -h / | tail -1
uv pip install -q ctranslate2==4.5.0   # only for the int8 copy at the end

T=data/nchlt_xho/transcriptions
SEEN="--train-xml $T/nchlt_xho.trn.xml --train-fleurs-tsv $F/train.tsv"
EVAL="python src/baseline.py --root data --language sw $SEEN"
NTEST="--xml $T/nchlt_xho.tst.xml --max-new-tokens 96"
FTEST="--fleurs-tsv $F/test.tsv --fleurs-audio $F/audio/test"
COMMON="--xml $T/nchlt_xho.trn.xml --root data --fleurs-tsv $F/train.tsv --fleurs-audio $F/audio/train
  --fleurs-dev-tsv $F/dev.tsv --fleurs-dev-audio $F/audio/dev --fleurs-dev-clips 200 --soapies-root data/soapies_engxho
  --english-xml data/nchlt_eng/transcriptions/nchlt_eng.trn.xml --english-hours 10
  --model init/R-0012 --batch-size 8 --grad-accum 4 --language sw --max-steps 2000 --lr 5e-6 --warmup 200
  --eval-every 250 --dev-clips 600 --generation-max-length 96"
keep() { aws s3 sync "out/$1" "s3://$BUCKET/jobs/R-0015/out/$1/" --only-show-errors; }
quiet() { grep --line-buffered -vE "^\s*$"; }

run() {  # run-id, extra train.py options
  local R=$1; shift
  echo "=== $R: train (from R-0012, 2000 steps) $*"
  mkdir -p "out/$R/model"
  python src/train.py $COMMON "$@" --out "model-$R" 2>&1 | quiet | tee "out/$R/train.log"
  cp "model-$R"/log_history.json "model-$R"/data_split.json "out/$R/model/"
  [ -f "model-$R/stitched.jsonl" ] && cp "model-$R/stitched.jsonl" "out/$R/model/"
  aws s3 sync "model-$R/final" "s3://$BUCKET/models/$R/" --only-show-errors   # kept (models/ never expires)
  ct2-transformers-converter --model "model-$R/final" --output_dir "int8-$R" --quantization int8 \
    --copy_files added_tokens.json generation_config.json merges.txt normalizer.json preprocessor_config.json \
    special_tokens_map.json tokenizer_config.json vocab.json
  aws s3 sync "int8-$R" "s3://$BUCKET/models/$R-int8/" --only-show-errors
  echo "=== $R: score on NCHLT test"
  $EVAL $NTEST --model "model-$R/final" --out "out/$R/eval_nchlt" 2>&1 | quiet | tee "out/$R/eval_nchlt.log"
  echo "=== $R: score on FLEURS test"
  $EVAL $FTEST --model "model-$R/final" --out "out/$R/eval_fleurs" 2>&1 | quiet | tee "out/$R/eval_fleurs.log"
  keep "$R"
  rm -rf "model-$R/checkpoints"   # 8.6 GB each; the final model is in S3
}

run R-0015
run R-0016 --stitch 8000
