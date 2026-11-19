#!/bin/bash
# R-0035 on one GPU node (L40S 48 GB, g6e.xlarge; g6e.2xlarge if short): whisper-medium retrained on R-0029's data
# (R-0019's data + the Swivuriso long-clip pieces, 309.7 h) with the fixed recipe (D-0031, Neon's pre-flight memo):
#   9000 steps (~2.9 epochs instead of 1.3), linear decay, lr 1e-5, warm-up 500 (only the length changes);
#   best checkpoint on 0.5 x Swivuriso dev CER + 0.5 x FLEURS dev CER (NCHLT dev for information);
#   SpecAugment with the attention mask; generation length 225 in the dev evaluations; 3 checkpoints kept.
# The job resumes: checkpoints are mirrored to S3 (jobs/R-0035/checkpoints/, expires with jobs/), and once the final
# model is in S3 (models/R-0035/COMPLETE) a relaunch skips training and only does what is missing. So a run cut off
# by the 6 h cap is relaunched with the same command and continues.
#   DISK_GB=300 FALLBACK_TYPES="g6e.2xlarge" cloud/run_job.sh --run R-0035 --type g6e.xlarge --market ondemand --max-hours 6
set -euo pipefail
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader; nproc; free -g | head -2
quiet() { grep --line-buffered -vE "^\s*$"; }
source cloud/node/test_data.sh
export CT2_USE_MKL=0
BASE_REV=abdf7c39ab9d0397620ccaea8974cc764cd0953e   # openai/whisper-medium on Hugging Face, pinned
MODELS="s3://$BUCKET/models"; CKS3="s3://$BUCKET/jobs/R-0035/checkpoints"
mkdir -p out/model model/checkpoints

echo "=== $(date -u +%T) software"
setup_ct2
python -c "from huggingface_hub import snapshot_download as d; d('openai/whisper-medium', revision='$BASE_REV', local_dir='base/whisper-medium', allow_patterns=['*.json', '*.txt', 'model.safetensors'])" >/dev/null
BASE=base/whisper-medium

echo "=== $(date -u +%T) data"
if aws s3 ls "$MODELS/R-0035/COMPLETE" >/dev/null 2>&1; then TRAINED=1; else TRAINED=0; fi
get_test_sets
if [ $TRAINED = 0 ]; then
  aws s3 sync "s3://$BUCKET/datasets/nchlt_xho/extracted/nchlt_xho/" data/nchlt_xho/ --only-show-errors
  get_fleurs train dev test
  aws s3 ls "s3://$BUCKET/datasets/swivuriso_xho_16k/COMPLETE" >/dev/null || { echo "prepared Swivuriso copy missing in S3"; exit 1; }
  aws s3 sync "s3://$BUCKET/datasets/swivuriso_xho_16k/" $S/ --only-show-errors
  aws s3 sync "s3://$BUCKET/datasets/swivuriso_xho_long/" data/swiv_long/ --only-show-errors
  cp $S/summary.json out/swivuriso_summary.json
  echo "audio: $(find data -name '*.wav' | wc -l) wav files"; df -h / | tail -1
  python - <<'PY'   # R-0029's training list: R-0019's short clips + every long-clip piece (R-0027's gate kept all)
import csv
csv.field_size_limit(10 ** 8)
FIELDS = ["id", "speaker", "type", "domain", "duration", "file", "text", "raw"]
short = list(csv.DictReader(open("data/swivuriso_16k/train.tsv", encoding="utf-8", newline=""), delimiter="\t"))
pieces = list(csv.DictReader(open("data/swiv_long/pieces.tsv", encoding="utf-8", newline=""), delimiter="\t"))
rows = short + [{**{k: p[k] for k in FIELDS if k in p}, "file": "../swiv_long/" + p["file"], "raw": p["text"]} for p in pieces]
with open("data/swiv_all_train.tsv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, FIELDS, delimiter="\t", extrasaction="ignore"); w.writeheader(); w.writerows(rows)
print(f"Swivuriso training rows: {len(short)} short clips + {len(pieces)} long-clip pieces")
PY
  python - <<'PY'   # every test and dev sentence (as R-0029); a Swivuriso training clip with one of these is dropped
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
fi

# The R-0035 recipe, every setting the run uses (the preflight below uses exactly these, plus a short length)
RECIPE="--xml $T/nchlt_xho.trn.xml --root data --fleurs-tsv $F/train.tsv --fleurs-audio $F/audio/train
  --fleurs-dev-tsv $F/dev.tsv --fleurs-dev-audio $F/audio/dev --fleurs-dev-clips 0
  --swivuriso-tsv data/swiv_all_train.tsv --swivuriso-audio $S --exclude-texts data/test_texts.txt
  --swivuriso-dev-tsv $S/dev.tsv --swivuriso-dev-audio $S --swivuriso-dev-per-speaker 22 --swivuriso-dev-max-tokens 220
  --model $BASE --language sw --lr 1e-5 --warmup 500 --lr-scheduler linear --generation-max-length 225
  --select-on swivuriso+fleurs --count-runaways --save-total-limit 3
  --spec-augment --mask-time-prob 0.05 --mask-time-length 10 --mask-time-min-masks 2
  --mask-feature-prob 0.10 --mask-feature-length 8 --mask-feature-min-masks 1"

if [ $TRAINED = 0 ]; then
  # runs/preflight.sh (whisper-small, defaults) is not used: preflight 2 runs the real model with every setting
  echo "=== $(date -u +%T) preflight 1/3: SpecAugment reaches whisper-medium (mask passed, masks on speech only, none in eval)"
  python src/check_specaug.py --model $BASE --swivuriso-tsv $S/dev.tsv --swivuriso-audio $S --clips 8 --trials 10 \
    --mask-time-prob 0.05 --mask-time-length 10 --mask-time-min-masks 2 --mask-feature-prob 0.10 \
    --mask-feature-length 8 --mask-feature-min-masks 1 2>&1 | quiet | grep -v past_key_values
  echo "=== $(date -u +%T) preflight 2/3: the full recipe, batch 8 x 4, the 16 longest transcripts, 2 steps, all dev sets"
  BATCH="--batch-size 8 --grad-accum 4"
  PRE="--train-longest 16 --max-steps 2 --eval-every 2 --warmup 1 --dev-clips 8 --fleurs-dev-clips 8 --swivuriso-dev-per-speaker 1"
  if ! python src/train.py $RECIPE $BATCH $PRE --out /tmp/pre 2>&1 | quiet | tail -n 4; then
    echo "=== batch 8 x 4 did not fit: trying 4 x 8 (same 32 clips per step)"   # P-0008: try every candidate
    rm -rf /tmp/pre; BATCH="--batch-size 4 --grad-accum 8"
    python src/train.py $RECIPE $BATCH $PRE --out /tmp/pre 2>&1 | quiet | tail -n 4
  fi
  python - <<'PY'
import json
h = json.load(open("/tmp/pre/log_history.json"))
keys = {k for x in h for k in x}
need = {"eval_nchlt_cer", "eval_fleurs_cer", "eval_swivuriso_cer", "eval_combined_cer", "eval_swivuriso_runaways"}
assert need <= keys, f"missing in the log: {need - keys}"
d = json.load(open("/tmp/pre/data_split.json"))
assert d["recipe"]["spec_augment"] and d["recipe"]["select_on"] == "swivuriso+fleurs", d["recipe"]
c = json.load(open("/tmp/pre/final/config.json"))
assert c["apply_spec_augment"] and c["mask_feature_prob"] == 0.1, "SpecAugment not saved in the model config"
print("recipe preflight OK:", sorted(need), "| Swivuriso dev:", d["recipe"]["swivuriso_dev_speakers"], "speakers")
PY
  echo "=== $(date -u +%T) preflight 3/3: int8 copy (P-0020) and the guarded evaluator on the GPU, 3 clips per set"
  python src/make_ct2.py convert --model /tmp/pre/final --out /tmp/pre-int8 --quantization int8 | tail -n 1
  for set in nchlt fleurs swivuriso soapies; do
    python src/eval_guarded.py --model /tmp/pre/final --cache /tmp/pre-ct2 --quantization float16 --device cuda \
      --compute-type float16 --limit 3 ${SET_ARGS[$set]} --out /tmp/pre-eval/$set 2>&1 | quiet | tail -n 1
  done
  CUDA_VISIBLE_DEVICES="" python src/eval_guarded.py --model /tmp/pre-int8 --device cpu --compute-type int8 --limit 1 \
    ${SET_ARGS[nchlt]} --out /tmp/pre-eval/int8 2>&1 | quiet | tail -n 1
  rm -rf /tmp/pre /tmp/pre-int8 /tmp/pre-ct2 /tmp/pre-eval
  echo "$BATCH" > out/batch.txt
  echo "=== $(date -u +%T) preflight passed ($BATCH)"

  # checkpoints -> S3, each one only when complete and with trainer_state.json last (a resume needs all of it)
  aws s3 sync "$CKS3/" model/checkpoints/ --only-show-errors   # a relaunch picks up where the last node stopped
  mirror() {
    for d in model/checkpoints/checkpoint-*; do
      [ -f "$d/trainer_state.json" ] && [ ! -f "$d/.in_s3" ] || continue
      n=$(basename $d)
      aws s3 sync "$d" "$CKS3/$n/" --exclude trainer_state.json --exclude .in_s3 --only-show-errors \
        && aws s3 cp "$d/trainer_state.json" "$CKS3/$n/" --only-show-errors && touch "$d/.in_s3"
    done
    for n in $(aws s3 ls "$CKS3/" | awk '{print $2}' | tr -d /); do   # the trainer keeps 3: so does S3
      [ -d "model/checkpoints/$n" ] || aws s3 rm "$CKS3/$n/" --recursive --only-show-errors
    done
  }
  ( while sleep 300; do mirror || true; done ) & MIRROR=$!

  echo "=== $(date -u +%T) R-0035: fine-tune whisper-medium, 9000 steps ($BATCH), evaluations every 1000"
  python src/train.py $RECIPE $BATCH --out model --max-steps 9000 --eval-every 1000 --dev-clips 600 2>&1 \
    | quiet | tee -a out/train.log
  kill $MIRROR 2>/dev/null || true; mirror
  cp model/log_history.json model/data_split.json out/model/
  aws s3 sync model/final "$MODELS/R-0035/" --only-show-errors && date -u +%FT%TZ | aws s3 cp - "$MODELS/R-0035/COMPLETE"
  FINAL=model/final
else
  echo "=== $(date -u +%T) R-0035 already trained (S3 models/R-0035/COMPLETE): evaluations only"
  aws s3 sync "$MODELS/R-0035/" model/final/ --only-show-errors --exclude COMPLETE
  FINAL=model/final
fi

echo "=== $(date -u +%T) int8 copy with processor files and tokenizer.json (P-0020) -> S3 models/R-0035-int8/"
if ! aws s3 ls "$MODELS/R-0035-int8/COMPLETE" >/dev/null 2>&1; then
  python src/make_ct2.py convert --model $FINAL --out models/R-0035-int8 --quantization int8 | tail -n 1
  aws s3 sync models/R-0035-int8/ "$MODELS/R-0035-int8/" --only-show-errors && date -u +%FT%TZ | aws s3 cp - "$MODELS/R-0035-int8/COMPLETE"
fi
FP16=$(python src/make_ct2.py convert --model $FINAL --out models/R-0035-fp16 --quantization float16 | tail -n 1)

# Evaluations, most important first (if the cap stops the node, relaunching does only what is missing):
# 1. the ship-rule decoding: loop guard, beam 5, CTranslate2 float16 (as R-0033 scores R-0019); 2. legacy greedy
# (src/baseline.py, as every run up to R-0029); 3. the beam 1 arm.
G="python src/eval_guarded.py --model $FP16 --device cuda --compute-type float16"
guarded() {  # guarded <beam> : the four sets side by side
  local pids=()
  for set in nchlt fleurs swivuriso soapies; do
    [ -f out/gpu_fp16_beam$1/eval_$set/metrics.json ] && continue
    $G --beam-size $1 ${SET_ARGS[$set]} $SEEN --label "R-0035 CT2 float16, beam $1 + loop guard" \
      --out out/gpu_fp16_beam$1/eval_$set > out/gpu_fp16_beam$1.$set.log 2>&1 & pids+=($!)
  done
  for p in "${pids[@]}"; do wait $p; done
  tail -q -n 1 out/gpu_fp16_beam$1.*.log
}
[ -f out/gpu_fp16_beam5/eval_nchlt/metrics.json ] || aws s3 sync "s3://$BUCKET/jobs/R-0035/out/" out/ --only-show-errors \
  --exclude "*" --include "gpu_fp16_beam*/*" --include "legacy_greedy/*"   # results of an earlier, cut-off node
echo "=== $(date -u +%T) R-0035 scoring 1/3: loop guard, beam 5"
guarded 5
echo "=== $(date -u +%T) R-0035 scoring 2/3: legacy transformers greedy (src/baseline.py, as R-0019 and R-0029)"
B="python src/baseline.py --language sw $SEEN --model $FINAL"
[ -f out/legacy_greedy/eval_nchlt/metrics.json ] || $B ${SET_ARGS[nchlt]} --max-new-tokens 96 --out out/legacy_greedy/eval_nchlt 2>&1 | quiet | tail -n 1
[ -f out/legacy_greedy/eval_fleurs/metrics.json ] || $B ${SET_ARGS[fleurs]} --out out/legacy_greedy/eval_fleurs 2>&1 | quiet | tail -n 1
[ -f out/legacy_greedy/eval_swivuriso/metrics.json ] || $B ${SET_ARGS[swivuriso]} --max-new-tokens 440 --out out/legacy_greedy/eval_swivuriso 2>&1 | quiet | tail -n 1
echo "=== $(date -u +%T) R-0035 scoring 3/3: loop guard, beam 1"
guarded 1
echo "=== $(date -u +%T) R-0035 done"
