#!/bin/bash
# R-0034: Meta Omnilingual ASR CTC v2 (300M, 1B; Apache 2.0) on the four test sets, scored like Thetha.
#   bash runs/R-0034/omni.sh setup|gpu|cpu      (called by runs/R-0033/job.sh, or runs/R-0034/job.sh alone)
# Needs the test data (get_test_sets). Writes to out/R-0034/. The phases are separate so the CPU timing runs alone.
#   setup: its own venv: Meta's official package at a pinned commit (version 0.2.0, the first with the v2 models; PyPI
#      stops at 0.1.0), Python 3.12, fairseq2 and the torch it wants; libsndfile from apt
#   gpu:   accuracy on the GPU (the package's default bfloat16, batches of 8): every clip of the four test sets
#   cpu:   CPU time per clip (GPU hidden, batch 1, 8 threads), float32 and bfloat16, on the same 50 seeded clips per set
#      that R-0033 times R-0019-int8 on
set -euo pipefail
source cloud/node/test_data.sh   # SET_ARGS, SEEN (bash arrays do not pass between scripts)
OMNI_COMMIT=81f51e224ce9e74b02cc2a3eaf21b2d91d743455   # main, 2025-12-30: __version__ 0.2.0, cards rc_models_v2.yaml
O=out/R-0034
OPY=/opt/omni-venv/bin/python
CPU_SAMPLE=${CPU_SAMPLE:-50}
PHASE=${1:?setup, gpu or cpu}
quiet() { grep --line-buffered -vE "^\s*$"; }
mkdir -p $O
export OMNI_COMMIT

if [ $PHASE = setup ]; then
echo "=== $(date -u +%T) R-0034: Omnilingual venv (commit $OMNI_COMMIT)"
(apt-get update -qq && apt-get install -y -qq libsndfile1) >/dev/null 2>&1 || echo "apt libsndfile1 skipped (may already be there)"
uv venv -q -p 3.12 /opt/omni-venv
VIRTUAL_ENV=/opt/omni-venv uv pip install -q \
  "omnilingual-asr @ git+https://github.com/facebookresearch/omnilingual-asr@$OMNI_COMMIT" jiwer==3.0.5 soundfile scipy
$OPY - <<'PY' | tee $O/omni_env.txt
import importlib.metadata as m, torch
v = m.version("omnilingual-asr")
assert v == "0.2.0", f"omnilingual-asr {v}: the v2 cards need 0.2.0"
print("omnilingual-asr", v, "fairseq2", m.version("fairseq2"), "torch", torch.__version__, "cuda", torch.cuda.is_available())
PY
echo "=== $(date -u +%T) R-0034 preflight: 3 FLEURS clips with the 300M model on the GPU"
$OPY src/eval_omni.py --model-card omniASR_CTC_300M_v2 --device cuda --batch-size 3 --limit 3 \
  ${SET_ARGS[fleurs]} --out /tmp/omni_preflight 2>&1 | quiet | tail -n 2
rm -rf /tmp/omni_preflight
fi

if [ $PHASE = gpu ]; then
for card in omniASR_CTC_300M_v2 omniASR_CTC_1B_v2; do
  tag=$(echo $card | sed 's/omniASR_CTC_//; s/_v2//' | tr 'A-Z' 'a-z')   # 300m, 1b
  for set in nchlt fleurs swivuriso soapies; do
    echo "=== $(date -u +%T) R-0034 $card GPU: $set"
    $OPY src/eval_omni.py --model-card $card --device cuda --batch-size 8 ${SET_ARGS[$set]} $SEEN \
      --out $O/ctc_${tag}_gpu/eval_$set 2>&1 | quiet | tail -n 1
  done
done
fi

if [ $PHASE = cpu ]; then
for card in omniASR_CTC_300M_v2 omniASR_CTC_1B_v2; do
  tag=$(echo $card | sed 's/omniASR_CTC_//; s/_v2//' | tr 'A-Z' 'a-z')
  for dtype in float32 bfloat16; do
    for set in nchlt fleurs swivuriso soapies; do
      echo "=== $(date -u +%T) R-0034 $card CPU $dtype: $set ($CPU_SAMPLE clips)"
      CUDA_VISIBLE_DEVICES="" $OPY src/eval_omni.py --model-card $card --device cpu --dtype $dtype --threads 8 \
        --sample $CPU_SAMPLE ${SET_ARGS[$set]} $SEEN --out $O/ctc_${tag}_cpu_$dtype/eval_$set 2>&1 | quiet | tail -n 1
    done
  done
done
fi
echo "=== $(date -u +%T) R-0034 $PHASE done"
