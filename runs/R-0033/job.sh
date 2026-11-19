#!/bin/bash
# R-0033 + R-0034 on one GPU node (default g6.2xlarge: NVIDIA L4, same Ada generation as R-0035's L40S; 8 vCPU).
# R-0033: R-0019 (the published medium, pinned revision) re-scored with the loop guard (src/eval_guarded.py) on the
#   four test sets, two arms on the same clips: beam 1 and beam 5, CTranslate2 float16 on the GPU. Then the published
#   int8 copy, beam 5, on the CPU: 50 seeded clips per set, timed (the copy the live page and Siyamthanda run).
#   First, a reproduction check: the old evaluator (src/baseline.py, transformers greedy) on NCHLT, FLEURS and
#   Swivuriso must give R-0019's recorded October scores again; if not, the job stops there (rule 1 in run.md).
# R-0034: Meta Omnilingual CTC 300M and 1B (runs/R-0034/omni.sh). Its venv is built while the reproduction check
#   runs; its GPU part runs alone after R-0033's GPU part; its CPU part runs last. An R-0034 failure is recorded
#   (out/R-0034/FAILED_PARTS) and never stops R-0033.
# Order on the GPU (Neon review F-03): reproduction check -> R-0033 in 3 lanes (~3 GB each, well under the L4's
#   22 GB; memory logged every minute) -> R-0034 alone. Then CPU timing, one job at a time.
# Outputs: out/... (R-0033) and out/R-0034/... (cloud/collect.sh R-0033 puts both in runs/R-0033/; then
#   mv runs/R-0033/R-0034/* runs/R-0034/).
set -euo pipefail
export AWS_DEFAULT_REGION=us-east-1
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader; nproc; free -g | head -2
quiet() { grep --line-buffered -vE "^\s*$"; }
source cloud/node/test_data.sh
export CT2_USE_MKL=0                 # as on the laptop (AMD CPU); recorded in every metrics.json
R0019_REPO=Ntlakanipho/whisper-medium-isixhosa
R0019_REV=603a39b5f70526ef2192e5d6f80f713c682a1d39   # Hugging Face main = R-0019 (model.safetensors + ct2-int8/)
CACHE=models_cache
O=out
CPU_SAMPLE=50
mkdir -p $O $O/R-0034

omni() {  # omni <phase> <timeout s>: R-0034 in a clean environment; a failure is recorded, R-0033 carries on
  if env -u LD_LIBRARY_PATH -u VIRTUAL_ENV -u PYTHONPATH timeout "$2" bash runs/R-0034/omni.sh "$1"; then
    echo "=== $(date -u +%T) R-0034 $1: OK"
  else
    echo "!!! $(date -u +%T) R-0034 $1 FAILED or timed out (see out/R-0034/omni.log); R-0033 carries on"
    echo "$1" >> $O/R-0034/FAILED; return 1
  fi
}

echo "=== $(date -u +%T) software"
setup_ct2
get_test_sets

echo "=== $(date -u +%T) R-0019 from Hugging Face @ $R0019_REV: full weights -> CTranslate2 float16, and the int8 copy"
FP16=$(timeout 1800 python src/make_ct2.py fetch --repo $R0019_REPO --revision $R0019_REV --variant full --quantization float16 --cache $CACHE | tail -n 1)
INT8=$(timeout 900 python src/make_ct2.py fetch --repo $R0019_REPO --revision $R0019_REV --variant ct2-int8 --cache $CACHE | tail -n 1)
FULL=$CACHE/whisper-medium-isixhosa@${R0019_REV:0:8}-full
ls $FP16 $INT8; du -sh $FP16 $INT8 $FULL
G="python src/eval_guarded.py --model"

echo "=== $(date -u +%T) preflight: 3 clips per set, both arms, GPU float16"
for set in nchlt fleurs swivuriso soapies; do
  for beam in 1 5; do
    $G $FP16 --device cuda --compute-type float16 --beam-size $beam --limit 3 ${SET_ARGS[$set]} \
      --out /tmp/preflight/$set-$beam > /tmp/preflight.log 2>&1 || { cat /tmp/preflight.log; exit 1; }
    grep "^{" /tmp/preflight.log
  done
done
rm -rf /tmp/preflight

omni setup 3600 > $O/R-0034/setup.log 2>&1 &   # venv + weights download (CPU and network only)
OMNI=$!

echo "=== $(date -u +%T) reproduction check: src/baseline.py (transformers greedy fp16, R-0019's October evaluator)"
B="python src/baseline.py --language sw $SEEN --model $FULL"
$B ${SET_ARGS[nchlt]} --max-new-tokens 96 --out $O/repro_greedy/eval_nchlt 2>&1 | quiet
$B ${SET_ARGS[fleurs]} --out $O/repro_greedy/eval_fleurs 2>&1 | quiet
$B ${SET_ARGS[swivuriso]} --max-new-tokens 440 --out $O/repro_greedy/eval_swivuriso 2>&1 | quiet
python - <<'PY' 2>&1 | tee $O/repro_check.txt
import json, sys
bad = 0
for s in ("nchlt", "fleurs", "swivuriso"):
    old = json.load(open(f"runs/R-0019/eval_{s}/metrics.json"))
    new = json.load(open(f"out/repro_greedy/eval_{s}/metrics.json"))
    same = old["clips"] == new["clips"] and abs(old["cer"] - new["cer"]) <= 0.05 and abs(old["wer"] - new["wer"]) <= 0.2
    bad += not same
    print(f"{s}: October {old['clips']} clips WER {old['wer']} CER {old['cer']} | now {new['clips']} clips "
          f"WER {new['wer']} CER {new['cer']} | {'REPRODUCED' if same else 'DIFFERENT'}")
if bad:
    print("REPRODUCTION CHECK FAILED: the data or the weights are not what R-0019 was scored on. Stopping (rule 1).")
    sys.exit(1)
print("reproduction check passed")
PY

echo "=== $(date -u +%T) R-0033 GPU float16: 3 lanes side by side"
arm() {  # arm <set> <beam>
  $G $FP16 --device cuda --compute-type float16 --beam-size $2 ${SET_ARGS[$1]} $SEEN \
    --label "R-0019 ($R0019_REPO@${R0019_REV:0:8}) CT2 float16, beam $2 + loop guard" \
    --out $O/gpu_fp16_beam$2/eval_$1 > $O/gpu_fp16_beam$2.$1.log 2>&1 || { tail -n 30 $O/gpu_fp16_beam$2.$1.log; return 1; }
}
monitor() {  # every minute: GPU memory (kept, the peak is reported) and each lane's latest progress line
  while true; do
    local mem; mem=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -n 1)
    echo "$mem" >> $O/gpu_memory_mib.txt
    echo "--- $(date -u +%T) GPU memory $mem MiB |$(for f in $O/gpu_fp16_beam*.log; do [ -f $f ] || continue
      echo -n " $(basename $f .log): $(grep -o '[0-9]*/[0-9]* clips' $f | tail -n 1)"; done)"
    sleep 60
  done
}
monitor & MON=$!
pids=()
arm swivuriso 5 & pids+=($!)
(arm swivuriso 1 && arm nchlt 5) & pids+=($!)
(arm fleurs 5 && arm fleurs 1 && arm nchlt 1 && arm soapies 5 && arm soapies 1) & pids+=($!)
fail=0; for p in "${pids[@]}"; do wait $p || fail=1; done
kill $MON 2>/dev/null || true
echo "R-0033 GPU peak memory: $(sort -n $O/gpu_memory_mib.txt 2>/dev/null | tail -n 1) MiB (of ~22 500)" | tee $O/gpu_peak.txt
grep -h "^{" $O/gpu_fp16_beam*.log || true
[ $fail = 0 ] || { echo "an R-0033 GPU scoring lane failed (its log is shown above)"; exit 1; }

wait $OMNI || true
tail -n 5 $O/R-0034/setup.log
if [ ! -s $O/R-0034/FAILED ]; then
  echo "=== $(date -u +%T) R-0034 GPU part, alone on the GPU"
  omni gpu 3600 || true
fi

echo "=== $(date -u +%T) CPU timing, one job at a time, nothing else running"
echo "=== $(date -u +%T) R-0033 CPU int8 (published copy), beam 5 + loop guard, $CPU_SAMPLE clips per set, 8 threads"
for set in nchlt fleurs swivuriso soapies; do
  CUDA_VISIBLE_DEVICES="" $G $INT8 --device cpu --compute-type int8 --threads 8 --beam-size 5 --sample $CPU_SAMPLE \
    --progress-every 10 ${SET_ARGS[$set]} $SEEN --label "R-0019 ($R0019_REPO@${R0019_REV:0:8}) ct2-int8, beam 5 + loop guard" \
    --out $O/cpu_int8_beam5/eval_$set 2>&1 | quiet
done
if ! grep -qx setup $O/R-0034/FAILED 2>/dev/null; then
  CPU_BUDGET=2700 omni cpu 3000 || true   # the CPU phase stops itself after 45 min; the timeout is a backstop
fi
lscpu | grep "Model name" | tee $O/cpu.txt
echo "=== $(date -u +%T) R-0033 done; R-0034: $([ -s $O/R-0034/FAILED ] && echo "FAILED parts: $(paste -sd' ' $O/R-0034/FAILED)" || echo OK)"
