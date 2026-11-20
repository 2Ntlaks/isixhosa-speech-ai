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
export AWS_DEFAULT_REGION=us-east-1
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader; nproc; free -g | head -2
quiet() { grep --line-buffered -vE "^\s*$"; }
source cloud/node/test_data.sh
export CT2_USE_MKL=0
BASE_REV=abdf7c39ab9d0397620ccaea8974cc764cd0953e   # openai/whisper-medium on Hugging Face, pinned
MODELS="s3://$BUCKET/models"; CKS3="s3://$BUCKET/jobs/R-0035/checkpoints"
mkdir -p out/model model/checkpoints

echo "=== $(date -u +%T) software"
setup_ct2
BASE=base/whisper-medium
if aws s3 ls "$MODELS/R-0035/COMPLETE" >/dev/null 2>&1; then TRAINED=1; else TRAINED=0; fi

echo "=== $(date -u +%T) data"
if [ $TRAINED = 0 ]; then   # the base model only when training (F-17)
  timeout 1800 python -c "from huggingface_hub import snapshot_download as d; d('openai/whisper-medium', revision='$BASE_REV', local_dir='$BASE', allow_patterns=['*.json', '*.txt', 'model.safetensors'])" >/dev/null
  get_fleurs train dev test   # first, so get_test_sets finds the test archive already here (no second download)
fi
get_test_sets
if [ $TRAINED = 0 ]; then
  aws s3 sync "s3://$BUCKET/datasets/nchlt_xho/extracted/nchlt_xho/" data/nchlt_xho/ --only-show-errors
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
  --select-on swivuriso+fleurs --count-runaways --save-total-limit 3 --check-audio
  --spec-augment --mask-time-prob 0.05 --mask-time-length 10 --mask-time-min-masks 2
  --mask-feature-prob 0.10 --mask-feature-length 8 --mask-feature-min-masks 1"

logged() {  # logged <name> <command...>: full output to out/<name>.log; its last 40 lines if it fails (F-08)
  local name=$1; shift
  "$@" > out/$name.log 2>&1 && return 0
  echo "!!! $name failed; last 40 lines of out/$name.log:"; tail -n 40 out/$name.log; return 1
}

if [ $TRAINED = 0 ]; then
  # runs/preflight.sh (whisper-small, defaults) is not used: preflight 3 runs the real model with every setting
  echo "=== $(date -u +%T) preflight 1/4: the full training data split must be R-0029's"
  logged split_check python src/train.py $RECIPE --split-only --out /tmp/split
  python - <<'PY'
import json
d = json.load(open("/tmp/split/data_split.json"))
r0029 = json.load(open("runs/R-0029/model/data_split.json"))
keys = ["train_clips", "train_hours", "train_speakers", "dev_speakers", "fleurs_train_clips", "fleurs_train_hours",
        "swivuriso_train_clips", "swivuriso_train_hours", "swivuriso_dropped_test_sentences",
        "swivuriso_dropped_over_440_tokens", "swivuriso_train_speakers"]
diff = {k: (d[k], r0029[k]) for k in keys if d[k] != r0029[k]}
assert not diff, f"the training data differs from R-0029's (now, R-0029): {diff}"
print("data split = R-0029's:", {k: d[k] for k in keys[:3]}, "| Swivuriso dev sample:",
      d["recipe"]["swivuriso_dev_clips_scored"], "clips,", d["recipe"]["swivuriso_dev_speakers"], "speakers,",
      d["recipe"]["swivuriso_dev_unscripted"], "unscripted")
PY
  echo "=== $(date -u +%T) preflight 2/4: SpecAugment reaches whisper-medium (mask passed, masks on speech only, none in eval)"
  logged specaug_check python src/check_specaug.py --model $BASE --swivuriso-tsv $S/dev.tsv --swivuriso-audio $S \
    --clips 8 --trials 10 --mask-time-prob 0.05 --mask-time-length 10 --mask-time-min-masks 2 --mask-feature-prob 0.10 \
    --mask-feature-length 8 --mask-feature-min-masks 1
  grep -E "^[1-4]\.|OK" out/specaug_check.log
  echo "=== $(date -u +%T) preflight 3/4: the full recipe, batch 8 x 4, the 16 longest transcripts, 2 steps, all dev sets"
  BATCH="--batch-size 8 --grad-accum 4"
  PRE="--train-longest 16 --max-steps 2 --eval-every 2 --warmup 1 --dev-clips 8 --fleurs-dev-clips 8 --swivuriso-dev-per-speaker 1"
  if ! logged recipe_check python src/train.py $RECIPE $BATCH $PRE --out /tmp/pre; then
    echo "=== batch 8 x 4 failed (above): trying 4 x 8 (same 32 clips per step)"   # P-0008: try every candidate
    rm -rf /tmp/pre; BATCH="--batch-size 4 --grad-accum 8"
    logged recipe_check_4x8 python src/train.py $RECIPE $BATCH $PRE --out /tmp/pre
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
print("recipe preflight OK:", sorted(need))
PY
  echo "=== $(date -u +%T) preflight 4/4: int8 copy (P-0020) and the guarded evaluator on the GPU, 3 clips per set"
  logged int8_check python src/make_ct2.py convert --model /tmp/pre/final --out /tmp/pre-int8 --quantization int8
  for set in nchlt fleurs swivuriso soapies; do
    logged guard_check_$set python src/eval_guarded.py --model /tmp/pre/final --cache /tmp/pre-ct2 --quantization float16 \
      --device cuda --compute-type float16 --limit 3 ${SET_ARGS[$set]} --out /tmp/pre-eval/$set
  done
  CUDA_VISIBLE_DEVICES="" logged guard_check_int8 python src/eval_guarded.py --model /tmp/pre-int8 --device cpu \
    --compute-type int8 --limit 1 ${SET_ARGS[nchlt]} --out /tmp/pre-eval/int8
  rm -rf /tmp/pre /tmp/pre-int8 /tmp/pre-ct2 /tmp/pre-eval /tmp/split
  echo "$BATCH" > out/batch.txt
  echo "=== $(date -u +%T) preflight passed ($BATCH)"

  # checkpoints -> S3, each one only when complete and with trainer_state.json last (a resume needs all of it).
  # Older S3 checkpoints are pruned only after every local one is confirmed in S3 (F-09).
  aws s3 sync "$CKS3/" model/checkpoints/ --only-show-errors   # a relaunch picks up where the last node stopped
  mirror() {
    local d n
    for d in model/checkpoints/checkpoint-*; do
      [ -f "$d/trainer_state.json" ] && [ ! -f "$d/.in_s3" ] || continue
      n=$(basename $d)
      aws s3 sync "$d" "$CKS3/$n/" --exclude trainer_state.json --exclude .in_s3 --only-show-errors || return 1
      aws s3 cp "$d/trainer_state.json" "$CKS3/$n/" --only-show-errors || return 1
      touch "$d/.in_s3"
    done
    for n in $(aws s3 ls "$CKS3/" | awk '{print $2}' | tr -d /); do   # the trainer keeps 3: so does S3
      [ -d "model/checkpoints/$n" ] || aws s3 rm "$CKS3/$n/" --recursive --only-show-errors || return 1
    done
  }
  ( while sleep 300; do mirror || echo "--- $(date -u +%T) checkpoint mirror failed; retrying in 5 min"; done ) & MIRROR=$!

  echo "=== $(date -u +%T) R-0035: fine-tune whisper-medium, 9000 steps ($BATCH), evaluations every 1000"
  python src/train.py $RECIPE $BATCH --out model --max-steps 9000 --eval-every 1000 --dev-clips 600 2>&1 \
    | quiet | tee -a out/train.log
  kill $MIRROR 2>/dev/null || true
  mirror || echo "--- final checkpoint mirror failed (the model upload below does not depend on it)"
  cp model/log_history.json model/data_split.json out/model/
  aws s3 sync out/model "s3://$BUCKET/jobs/R-0035/out/model/" --only-show-errors   # records first (F-09), then the model
  aws s3 cp out/train.log "s3://$BUCKET/jobs/R-0035/out/train.log" --only-show-errors
  aws s3 sync model/final "$MODELS/R-0035/" --only-show-errors
  date -u +%FT%TZ | aws s3 cp - "$MODELS/R-0035/COMPLETE"
  FINAL=model/final
else
  echo "=== $(date -u +%T) R-0035 already trained (S3 models/R-0035/COMPLETE): evaluations only"
  aws s3 sync "$MODELS/R-0035/" model/final/ --only-show-errors --exclude COMPLETE
  FINAL=model/final
fi
FP16=$(python src/make_ct2.py convert --model $FINAL --out models/R-0035-fp16 --quantization float16 | tail -n 1)

# Evaluations, most important first (if the cap stops the node, relaunching does only what is missing):
# 1. the ship-rule decoding: loop guard, beam 5, CTranslate2 float16 (as R-0033 scores R-0019), four sets;
# 2. the old evaluator (src/baseline.py, transformers greedy, as every run up to R-0029), three October sets;
# 3. the int8 copy for the laptop and Siyamthanda. (No beam-1 arm: R-0033 already isolates the guard; F-13.)
[ -f out/gpu_fp16_beam5/eval_nchlt/metrics.json ] || aws s3 sync "s3://$BUCKET/jobs/R-0035/out/" out/ --only-show-errors \
  --exclude "*" --include "gpu_fp16_beam5/*" --include "gpu_fp16_beam5.*.log" --include "legacy_greedy/*"
G="python src/eval_guarded.py --model $FP16 --device cuda --compute-type float16"
guarded() {  # guarded <beam>: the sets still missing, side by side, with a progress line every minute
  local pids=() logs=() set fail=0 p f mon
  for set in nchlt fleurs swivuriso soapies; do
    [ -f out/gpu_fp16_beam$1/eval_$set/metrics.json ] && { echo "$set: already scored"; continue; }
    $G --beam-size $1 ${SET_ARGS[$set]} $SEEN --label "R-0035 CT2 float16, beam $1 + loop guard" \
      --out out/gpu_fp16_beam$1/eval_$set > out/gpu_fp16_beam$1.$set.log 2>&1 & pids+=($!)
    logs+=(out/gpu_fp16_beam$1.$set.log)
  done
  [ ${#pids[@]} -gt 0 ] || return 0   # everything scored on an earlier node (F-01)
  ( while sleep 60; do echo "--- $(date -u +%T) GPU $(nvidia-smi --query-gpu=memory.used --format=csv,noheader | head -n 1) |$(
      for f in "${logs[@]}"; do echo -n " $(basename $f .log): $(grep -o '[0-9]*/[0-9]* clips' $f | tail -n 1)"; done)"; done ) &
  mon=$!
  for p in "${pids[@]}"; do wait $p || fail=1; done
  kill $mon 2>/dev/null || true
  for f in "${logs[@]}"; do if grep -q "^{" $f; then grep "^{" $f; else echo "!!! $f:"; tail -n 30 $f; fi; done
  return $fail
}
echo "=== $(date -u +%T) R-0035 scoring 1/2: loop guard, beam 5, four sets"
guarded 5
echo "=== $(date -u +%T) R-0035 scoring 2/2: old evaluator (src/baseline.py transformers greedy, as R-0019 and R-0029)"
B="python src/baseline.py --language sw $SEEN --model $FINAL"
[ -f out/legacy_greedy/eval_nchlt/metrics.json ] || $B ${SET_ARGS[nchlt]} --max-new-tokens 96 --out out/legacy_greedy/eval_nchlt 2>&1 | quiet
[ -f out/legacy_greedy/eval_fleurs/metrics.json ] || $B ${SET_ARGS[fleurs]} --out out/legacy_greedy/eval_fleurs 2>&1 | quiet
[ -f out/legacy_greedy/eval_swivuriso/metrics.json ] || $B ${SET_ARGS[swivuriso]} --max-new-tokens 440 --out out/legacy_greedy/eval_swivuriso 2>&1 | quiet

echo "=== $(date -u +%T) int8 copy with processor files and tokenizer.json (P-0020) -> S3 models/R-0035-int8/"
if ! aws s3 ls "$MODELS/R-0035-int8/COMPLETE" >/dev/null 2>&1; then
  python src/make_ct2.py convert --model $FINAL --out models/R-0035-int8 --quantization int8 | tail -n 1
  aws s3 sync models/R-0035-int8/ "$MODELS/R-0035-int8/" --only-show-errors
  date -u +%FT%TZ | aws s3 cp - "$MODELS/R-0035-int8/COMPLETE"
fi
echo "=== $(date -u +%T) R-0035 done"
