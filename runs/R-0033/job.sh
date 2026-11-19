#!/bin/bash
# R-0033 + R-0034 on one GPU node (default g6.2xlarge: NVIDIA L4, same Ada generation as R-0035's L40S; 8 vCPU).
# R-0033: R-0019 (the published medium, pinned revision) re-scored with the loop guard (src/eval_guarded.py) on the
#   four test sets, two arms on the same clips: beam 1 and beam 5, CTranslate2 float16 on the GPU. Then the published
#   int8 copy, beam 5, on the CPU: 50 seeded clips per set, timed (the copy the live page and Siyamthanda run).
#   First, a reproduction check: the old evaluator (src/baseline.py, transformers greedy) on NCHLT, FLEURS and
#   Swivuriso must give R-0019's recorded October scores again, which proves the data and the model are the same.
# R-0034: Meta Omnilingual CTC 300M and 1B on the same sets (runs/R-0034/omni.sh), its venv built while R-0033's
#   GPU runs work.
# Outputs: out/... (R-0033) and out/R-0034/... (cloud/collect.sh R-0033 puts both in runs/R-0033/; move R-0034/ to runs/R-0034/).
set -euo pipefail
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader; nproc; free -g | head -2
quiet() { grep --line-buffered -vE "^\s*$"; }
source cloud/node/test_data.sh
export CT2_USE_MKL=0                 # as on the laptop (AMD CPU); recorded in every metrics.json
R0019_REPO=Ntlakanipho/whisper-medium-isixhosa
R0019_REV=603a39b5f70526ef2192e5d6f80f713c682a1d39   # Hugging Face main = R-0019 (model.safetensors + ct2-int8/)
CACHE=models_cache
O=out
CPU_SAMPLE=50
mkdir -p $O

echo "=== $(date -u +%T) software"
setup_ct2
get_test_sets

echo "=== $(date -u +%T) R-0019 from Hugging Face @ $R0019_REV: full weights -> CTranslate2 float16, and the int8 copy"
FP16=$(python src/make_ct2.py fetch --repo $R0019_REPO --revision $R0019_REV --variant full --quantization float16 --cache $CACHE | tail -n 1)
INT8=$(python src/make_ct2.py fetch --repo $R0019_REPO --revision $R0019_REV --variant ct2-int8 --cache $CACHE | tail -n 1)
FULL=$CACHE/whisper-medium-isixhosa@${R0019_REV:0:8}-full
ls $FP16 $INT8; du -sh $FP16 $INT8 $FULL
G="python src/eval_guarded.py --model"

echo "=== $(date -u +%T) preflight: 3 clips per set, both arms, GPU float16"
for set in nchlt fleurs swivuriso soapies; do
  for beam in 1 5; do
    $G $FP16 --device cuda --compute-type float16 --beam-size $beam --limit 3 ${SET_ARGS[$set]} \
      --out /tmp/preflight/$set-$beam 2>&1 | quiet | tail -n 1
  done
done
rm -rf /tmp/preflight

bash runs/R-0034/omni.sh setup > out/omni_setup.log 2>&1 &
OMNI=$!   # R-0034's venv and its 3-clip preflight, while the reproduction check runs

echo "=== $(date -u +%T) reproduction check: src/baseline.py (transformers greedy fp16, R-0019's October evaluator)"
B="python src/baseline.py --language sw $SEEN --model $FULL"
$B ${SET_ARGS[nchlt]} --max-new-tokens 96 --out $O/repro_greedy/eval_nchlt 2>&1 | quiet | tail -n 1
$B ${SET_ARGS[fleurs]} --out $O/repro_greedy/eval_fleurs 2>&1 | quiet | tail -n 1
$B ${SET_ARGS[swivuriso]} --max-new-tokens 440 --out $O/repro_greedy/eval_swivuriso 2>&1 | quiet | tail -n 1
python - <<'PY' | tee $O/repro_check.txt
import json
for s in ("nchlt", "fleurs", "swivuriso"):
    old = json.load(open(f"runs/R-0019/eval_{s}/metrics.json"))
    new = json.load(open(f"out/repro_greedy/eval_{s}/metrics.json"))
    same = old["clips"] == new["clips"] and abs(old["cer"] - new["cer"]) <= 0.05 and abs(old["wer"] - new["wer"]) <= 0.2
    print(f"{s}: October {old['clips']} clips WER {old['wer']} CER {old['cer']} | now {new['clips']} clips "
          f"WER {new['wer']} CER {new['cer']} | {'REPRODUCED' if same else 'DIFFERENT: check data and model'}")
PY

wait $OMNI || { echo "R-0034 setup failed:"; tail -n 20 out/omni_setup.log; exit 1; }
tail -n 4 out/omni_setup.log

echo "=== $(date -u +%T) R-0033 GPU float16: 5 lanes side by side (~2.5 GB each), and R-0034's GPU part next to them"
arm() {  # arm <set> <beam>
  $G $FP16 --device cuda --compute-type float16 --beam-size $2 ${SET_ARGS[$1]} $SEEN \
    --label "R-0019 ($R0019_REPO@${R0019_REV:0:8}) CT2 float16, beam $2 + loop guard" \
    --out $O/gpu_fp16_beam$2/eval_$1 > $O/gpu_fp16_beam$2.$1.log 2>&1
}
bash runs/R-0034/omni.sh gpu > out/omni_gpu.log 2>&1 &
pids=($!)
arm swivuriso 5 & pids+=($!)
arm swivuriso 1 & pids+=($!)
(arm fleurs 5 && arm fleurs 1) & pids+=($!)
(arm nchlt 5 && arm nchlt 1) & pids+=($!)
(arm soapies 5 && arm soapies 1) & pids+=($!)
( while sleep 300; do nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader; done ) & MON=$!
fail=0; for p in "${pids[@]}"; do wait $p || fail=1; done
kill $MON 2>/dev/null || true
tail -q -n 1 $O/gpu_fp16_beam*.log; grep "^{" out/omni_gpu.log || true
[ $fail = 0 ] || { echo "a GPU scoring job failed (logs in $O and out/omni_gpu.log)"; exit 1; }

echo "=== $(date -u +%T) CPU timing, one job at a time, nothing else running"
echo "=== $(date -u +%T) R-0033 CPU int8 (published copy), beam 5 + loop guard, $CPU_SAMPLE clips per set, 8 threads, alone"
for set in nchlt fleurs swivuriso soapies; do
  CUDA_VISIBLE_DEVICES="" $G $INT8 --device cpu --compute-type int8 --threads 8 --beam-size 5 --sample $CPU_SAMPLE \
    ${SET_ARGS[$set]} $SEEN --label "R-0019 ($R0019_REPO@${R0019_REV:0:8}) ct2-int8, beam 5 + loop guard" \
    --out $O/cpu_int8_beam5/eval_$set 2>&1 | quiet | tail -n 1
done
bash runs/R-0034/omni.sh cpu 2>&1 | tee out/omni_cpu.log | grep --line-buffered "^===\|^{"
lscpu | grep "Model name" | tee $O/cpu.txt
echo "=== $(date -u +%T) R-0033 and R-0034 done"
