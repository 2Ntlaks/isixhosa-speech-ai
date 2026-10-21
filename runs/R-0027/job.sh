#!/bin/bash
# R-0027 on one GPU node (L40S 48 GB, g6e.xlarge): use Swivuriso's long clips, then train the small model for the demo.
#   1. Long clips (train split, > 30 s) -> pieces of at most 28 s cut at pauses (src/swivuriso_long.py), cached in S3
#      datasets/swivuriso_xho_long/ so later runs (the medium model) skip this step.
#   2. Quality gate (runs/R-0027/gate.py): R-0019 transcribes 600 random pieces; badly aligned pieces are dropped by
#      alignment score; if the kept pieces still score badly, the job stops here, before any training.
#   3. R-0007's model on Swivuriso test: the "before" for the small model (never measured).
#   4. whisper-small, R-0007's recipe + all usable Swivuriso (short clips as in R-0019 + the new pieces). Scored on
#      NCHLT test, FLEURS test, Swivuriso test.
set -euo pipefail
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
quiet() { grep --line-buffered -vE "^\s*$"; }
bash runs/preflight.sh

aws s3 sync "s3://$BUCKET/datasets/nchlt_xho/extracted/nchlt_xho/" data/nchlt_xho/ --only-show-errors
F=data/fleurs_xh_za
aws s3 sync "s3://$BUCKET/datasets/fleurs_xh_za/" $F/ --only-show-errors
for s in train dev test; do tar xzf $F/audio/$s.tar.gz -C $F/audio/; done
S=data/swivuriso_16k
aws s3 sync "s3://$BUCKET/datasets/swivuriso_xho_16k/" $S/ --only-show-errors
echo "audio: $(find data -name '*.wav' | wc -l) wav files"; df -h / | tail -1

T=data/nchlt_xho/transcriptions
python - <<'PY'   # every test and dev sentence (same as R-0019)
import sys
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

L=data/swiv_long; LC="s3://$BUCKET/datasets/swivuriso_xho_long"
if aws s3 ls "$LC/COMPLETE" >/dev/null 2>&1; then
  echo "=== $(date -u +%T) long clips: cut copy found in S3"
  aws s3 sync "$LC/" $L/ --only-show-errors
else
  echo "=== $(date -u +%T) long clips: extracting from the parquet shards"
  python src/swivuriso_long.py extract --source "s3://$BUCKET/datasets/swivuriso_xho/xho/" --out $L \
    --exclude-texts data/test_texts.txt --workers 4 2>&1 | quiet   # 4: also fits a 16 GB node
  df -h / | tail -1
  echo "=== $(date -u +%T) long clips: word timings and cutting (GPU)"
  python src/swivuriso_long.py cut --out $L --delete-long 2>&1 | quiet
  aws s3 sync $L/ "$LC/" --only-show-errors --exclude "long/*" && date -u +%FT%TZ | aws s3 cp - "$LC/COMPLETE"
fi
cp $L/extract_summary.json $L/cut_summary.json out/

EVAL="python src/baseline.py --root data --language sw --train-xml $T/nchlt_xho.trn.xml --train-fleurs-tsv $F/train.tsv"
echo "=== $(date -u +%T) quality gate: R-0019 on 600 random pieces"
python - <<'PY'
import csv, random
csv.field_size_limit(10 ** 8)
rows = list(csv.DictReader(open("data/swiv_long/pieces.tsv", encoding="utf-8", newline=""), delimiter="\t"))
pick = random.Random(1).sample(rows, min(600, len(rows)))
with open("data/gate_sample.tsv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, list(rows[0]), delimiter="\t"); w.writeheader(); w.writerows(pick)
PY
aws s3 sync "s3://$BUCKET/models/R-0019/" models/R-0019/ --only-show-errors
$EVAL --swivuriso-tsv data/gate_sample.tsv --swivuriso-audio $L --max-new-tokens 440 --model models/R-0019 \
  --out out/gate_r0019 2>&1 | quiet | tail -3
python runs/R-0027/gate.py $L/pieces.tsv out/gate_r0019/predictions.jsonl data/train_pieces.tsv out/gate.json \
  || { echo "=== quality gate FAILED: no training (see out/gate.json)"; exit 1; }
rm -rf models/R-0019

python - <<'PY'   # one training TSV: R-0019's short clips + the kept pieces (paths relative to data/swivuriso_16k)
import csv
csv.field_size_limit(10 ** 8)
FIELDS = ["id", "speaker", "type", "domain", "duration", "file", "text", "raw"]
short = list(csv.DictReader(open("data/swivuriso_16k/train.tsv", encoding="utf-8", newline=""), delimiter="\t"))
pieces = list(csv.DictReader(open("data/train_pieces.tsv", encoding="utf-8", newline=""), delimiter="\t"))
rows = short + [{**{k: p[k] for k in FIELDS if k in p}, "file": "../swiv_long/" + p["file"], "raw": p["text"]} for p in pieces]
with open("data/swiv_all_train.tsv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, FIELDS, delimiter="\t", extrasaction="ignore"); w.writeheader(); w.writerows(rows)
print(f"Swivuriso training rows: {len(short)} short clips + {len(pieces)} long-clip pieces")
PY

STEST="--swivuriso-tsv $S/dev_test.tsv --swivuriso-audio $S --max-new-tokens 440"
echo "=== $(date -u +%T) R-0007 (today's demo model) on Swivuriso test"
aws s3 sync "s3://$BUCKET/models/R-0007/" models/R-0007/ --only-show-errors
mkdir -p out/R-0007
$EVAL $STEST --model models/R-0007 --out out/R-0007/eval_swivuriso 2>&1 | quiet | tail -3 || echo "=== R-0007 eval FAILED (training continues)"

echo "=== $(date -u +%T) R-0027: fine-tune whisper-small 4000 steps on NCHLT + FLEURS + all usable Swivuriso"
mkdir -p out/model
python src/train.py --xml $T/nchlt_xho.trn.xml --root data --fleurs-tsv $F/train.tsv --fleurs-audio $F/audio/train \
  --fleurs-dev-tsv $F/dev.tsv --fleurs-dev-audio $F/audio/dev --fleurs-dev-clips 200 \
  --swivuriso-tsv data/swiv_all_train.tsv --swivuriso-audio $S --exclude-texts data/test_texts.txt \
  --model openai/whisper-small --out model --language sw --max-steps 4000 --eval-every 500 --dev-clips 600 \
  --generation-max-length 96 2>&1 | quiet | tee out/train.log
cp model/log_history.json model/data_split.json out/model/
aws s3 sync model/final "s3://$BUCKET/models/R-0027/" --only-show-errors   # kept (models/ never expires)

NTEST="--xml $T/nchlt_xho.tst.xml --max-new-tokens 96"
FTEST="--fleurs-tsv $F/test.tsv --fleurs-audio $F/audio/test"
echo "=== $(date -u +%T) R-0027: score on NCHLT test"
$EVAL $NTEST --model model/final --out out/eval_nchlt 2>&1 | quiet | tee out/eval_nchlt.log
echo "=== $(date -u +%T) R-0027: score on FLEURS test"
$EVAL $FTEST --model model/final --out out/eval_fleurs 2>&1 | quiet | tee out/eval_fleurs.log
echo "=== $(date -u +%T) R-0027: score on Swivuriso test"
$EVAL $STEST --model model/final --out out/eval_swivuriso 2>&1 | quiet | tee out/eval_swivuriso.log
echo "=== $(date -u +%T) done"
