#!/bin/bash
# R-0029 on one GPU node (L40S 48 GB, g6e): whisper-medium, R-0019's recipe with ONE change: the 98.9 h of Swivuriso
# long-clip pieces (cut and quality-checked in R-0027, cached in S3 datasets/swivuriso_xho_long/) added to training.
# Scored on NCHLT test, FLEURS test and Swivuriso test, like R-0019. Final model to S3 models/R-0029/.
set -euo pipefail
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
quiet() { grep --line-buffered -vE "^\s*$"; }
keep() { aws s3 sync "out/$1" "s3://$BUCKET/jobs/$1/out/" --only-show-errors; }
bash runs/preflight.sh

aws s3 sync "s3://$BUCKET/datasets/nchlt_xho/extracted/nchlt_xho/" data/nchlt_xho/ --only-show-errors
F=data/fleurs_xh_za
aws s3 sync "s3://$BUCKET/datasets/fleurs_xh_za/" $F/ --only-show-errors
for s in train dev test; do tar xzf $F/audio/$s.tar.gz -C $F/audio/; done
echo "audio: $(find data -name '*.wav' | wc -l) wav files"; df -h / | tail -1

S=data/swivuriso_16k; SC="s3://$BUCKET/datasets/swivuriso_xho_16k"
if aws s3 ls "$SC/COMPLETE" >/dev/null 2>&1; then
  echo "=== $(date -u +%T) Swivuriso: prepared copy found in S3"
  aws s3 sync "$SC/" $S/ --only-show-errors
else
  echo "=== $(date -u +%T) Swivuriso: preparing from the parquet shards"
  python src/swivuriso.py prepare --source "s3://$BUCKET/datasets/swivuriso_xho/xho/" --out $S --workers 6 2>&1 | quiet
  aws s3 sync $S/ "$SC/" --only-show-errors && date -u +%FT%TZ | aws s3 cp - "$SC/COMPLETE"
fi
cp $S/summary.json out/swivuriso_summary.json
echo "Swivuriso: $(find $S -name '*.wav' | wc -l) wav files"; df -h / | tail -1

L=data/swiv_long
aws s3 sync "s3://$BUCKET/datasets/swivuriso_xho_long/" $L/ --only-show-errors
python - <<'PY'   # R-0019's short clips + every R-0027 piece (its gate kept all), paths relative to data/swivuriso_16k
import csv
csv.field_size_limit(10 ** 8)
FIELDS = ["id", "speaker", "type", "domain", "duration", "file", "text", "raw"]
short = list(csv.DictReader(open("data/swivuriso_16k/train.tsv", encoding="utf-8", newline=""), delimiter="	"))
pieces = list(csv.DictReader(open("data/swiv_long/pieces.tsv", encoding="utf-8", newline=""), delimiter="	"))
rows = short + [{**{k: p[k] for k in FIELDS if k in p}, "file": "../swiv_long/" + p["file"], "raw": p["text"]} for p in pieces]
with open("data/swiv_all_train.tsv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, FIELDS, delimiter="	", extrasaction="ignore"); w.writeheader(); w.writerows(rows)
print(f"Swivuriso training rows: {len(short)} short clips + {len(pieces)} long-clip pieces")
PY

T=data/nchlt_xho/transcriptions
python - <<'PY'   # every test and dev sentence; a Swivuriso training clip with one of these is dropped
import csv, sys
sys.path.insert(0, "src")
import fleurs, nchlt, swivuriso
from scoring import normalise
T, F, S = "data/nchlt_xho/transcriptions", "data/fleurs_xh_za", "data/swivuriso_16k"
texts = {normalise(c["text"]) for c in nchlt.load_split(f"{T}/nchlt_xho.tst.xml", "data")}
for s in ("dev", "test"):
    texts |= {normalise(c["text"]) for c in fleurs.load_split(f"{F}/{s}.tsv", "")}
for s in ("dev", "dev_test"):
    texts |= {c["text"] for c in swivuriso.load_split(f"{S}/{s}.tsv", S)}
open("data/test_texts.txt", "w", encoding="utf-8").write("\n".join(sorted(t for t in texts if t)) + "\n")
print(f"{len(texts)} test/dev sentences kept out of training")
PY

echo "=== $(date -u +%T) memory check: whisper-medium, batch 8, the 16 longest transcripts"
BATCH="--batch-size 8 --grad-accum 4"
SWIV="--swivuriso-tsv data/swiv_all_train.tsv --swivuriso-audio $S --exclude-texts data/test_texts.txt"
if ! python src/train.py --xml $T/nchlt_xho.trn.xml --root data $SWIV --model openai/whisper-medium --batch-size 8 \
     --grad-accum 1 --train-longest 16 --out /tmp/memcheck --max-steps 2 --eval-every 2 --dev-clips 8 --warmup 1 \
     --generation-max-length 96 2>&1 | quiet | tail -4; then
  echo "=== memory check failed: falling back to batch 4 x grad-accum 8 (same 32 clips per step)"
  BATCH="--batch-size 4 --grad-accum 8"
fi
rm -rf /tmp/memcheck

SEEN="--train-xml $T/nchlt_xho.trn.xml --train-fleurs-tsv $F/train.tsv"
EVAL="python src/baseline.py --root data --language sw $SEEN"
NTEST="--xml $T/nchlt_xho.tst.xml --max-new-tokens 96"
FTEST="--fleurs-tsv $F/test.tsv --fleurs-audio $F/audio/test"
STEST="--swivuriso-tsv $S/dev_test.tsv --swivuriso-audio $S --max-new-tokens 440"

echo "=== $(date -u +%T) R-0029: fine-tune whisper-medium 4000 steps on NCHLT + FLEURS + Swivuriso train + long-clip pieces ($BATCH)"
mkdir -p out/model
python src/train.py --xml $T/nchlt_xho.trn.xml --root data --fleurs-tsv $F/train.tsv --fleurs-audio $F/audio/train \
  --fleurs-dev-tsv $F/dev.tsv --fleurs-dev-audio $F/audio/dev --fleurs-dev-clips 200 $SWIV \
  --model openai/whisper-medium $BATCH \
  --out model --language sw --max-steps 4000 --eval-every 500 --dev-clips 600 --generation-max-length 96 2>&1 \
  | quiet | tee out/train.log
cp model/log_history.json model/data_split.json out/model/
aws s3 sync model/final "s3://$BUCKET/models/R-0029/" --only-show-errors   # kept (models/ never expires)

echo "=== $(date -u +%T) R-0029: score on NCHLT test"
$EVAL $NTEST --model model/final --out out/eval_nchlt 2>&1 | quiet | tee out/eval_nchlt.log
echo "=== $(date -u +%T) R-0029: score on FLEURS test"
$EVAL $FTEST --model model/final --out out/eval_fleurs 2>&1 | quiet | tee out/eval_fleurs.log
echo "=== $(date -u +%T) R-0029: score on Swivuriso test"
$EVAL $STEST --model model/final --out out/eval_swivuriso 2>&1 | quiet | tee out/eval_swivuriso.log
