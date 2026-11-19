#!/bin/bash
# R-0034: Meta Omnilingual ASR CTC v2 (300M, 1B; Apache 2.0) on the four test sets, scored like Thetha.
#   bash runs/R-0034/omni.sh setup|gpu|cpu      (called by runs/R-0033/job.sh, or runs/R-0034/job.sh alone)
# Needs the test data (get_test_sets). Writes to $OMNI_OUT (default out/R-0034/), full log in $OMNI_OUT/omni.log.
#   setup: its own venv: Meta's official package at a pinned commit (version 0.2.0, the first with the v2 models; PyPI
#          stops at 0.1.0), Python 3.12, fairseq2 and the torch it wants; libsndfile; both models' weights downloaded
#   gpu:   accuracy on the GPU (the package's default bfloat16), every clip of the four test sets, run ALONE on the GPU.
#          Each model first runs one batch of the longest real clips (~30 s) at batch 8; out of memory -> 4 -> 2 -> 1.
#   cpu:   CPU time per clip (GPU hidden, batch 1, 8 threads), float32, on the same 50 seeded clips per set that
#          R-0033 times R-0019-int8 on; plus a 20-clip FLEURS probe of 300M in bfloat16 vs float32 (Meta issue #57:
#          bfloat16 can be much slower on CPUs without bfloat16 instructions). A time budget (CPU_BUDGET seconds)
#          bounds the whole phase.
# A failed step is recorded ($OMNI_OUT/FAILED_PARTS) and the others still run; the script then exits 1, and the
# caller carries on (an R-0034 failure never stops R-0033).
set -uo pipefail                 # no -e: one failed test set must not stop the others
source cloud/node/test_data.sh   # SET_ARGS, SEEN, AWS region (bash arrays do not pass between scripts)
# A clean environment (Neon review F-02): the job venv's CUDA library path and Python settings must not reach Meta's
# venv, which brings its own torch and CUDA libraries.
unset LD_LIBRARY_PATH VIRTUAL_ENV PYTHONPATH PYTHONHOME
PATH=$(echo "$PATH" | tr ':' '\n' | grep -v "/\.venv/" | paste -sd: -)
OMNI_COMMIT=81f51e224ce9e74b02cc2a3eaf21b2d91d743455   # main, 2025-12-30: __version__ 0.2.0, cards rc_models_v2.yaml
O=${OMNI_OUT:-out/R-0034}
OPY=${OMNI_PY:-/opt/omni-venv/bin/python}
CPU_SAMPLE=${CPU_SAMPLE:-50}
CPU_BUDGET=${CPU_BUDGET:-2700}   # seconds for the whole CPU phase
PHASE=${1:?setup, gpu or cpu}
CARDS="omniASR_CTC_300M_v2 omniASR_CTC_1B_v2"
SHOW="clips,|^\{|Error|error|Traceback|memory|Killed"   # what reaches node.log; everything goes to omni.log
mkdir -p $O
export OMNI_COMMIT
fails=0

attempt() {  # attempt <timeout s> <label> <command...>: full output to omni.log, progress lines to node.log
  local t=$1 label=$2; shift 2
  echo "=== $(date -u +%T) R-0034 $label"
  timeout "$t" "$@" 2>&1 | tee -a $O/omni.log | { grep --line-buffered -E "$SHOW" || true; }
  local rc=${PIPESTATUS[0]}
  [ $rc -eq 0 ] || echo "--- R-0034 $label: exit $rc$([ $rc -eq 124 ] && echo ' (timed out)')"
  return $rc
}
step() {  # step: as attempt, but a failure is recorded and the phase carries on
  local label=$2
  attempt "$@" && return 0
  fails=$((fails + 1)); echo "$label" >> $O/FAILED_PARTS
  echo "!!! R-0034 $label FAILED; last lines of its log:"; tail -n 15 $O/omni.log
  return 1
}
tag() { echo $1 | sed 's/omniASR_CTC_//; s/_v2//' | tr 'A-Z' 'a-z'; }   # 300m, 1b

if [ $PHASE = setup ]; then
  attempt 600 "apt libsndfile1" bash -c "apt-get update -qq && apt-get install -y -qq libsndfile1" \
    || echo "libsndfile1 not installed by apt (may already be there)"
  step 300 "venv" uv venv -q -p 3.12 /opt/omni-venv || exit 1
  step 1500 "install (commit $OMNI_COMMIT)" env VIRTUAL_ENV=/opt/omni-venv uv pip install -q \
    "omnilingual-asr @ git+https://github.com/facebookresearch/omnilingual-asr@$OMNI_COMMIT" \
    jiwer==3.0.5 soundfile scipy || exit 1
  step 120 "version check" $OPY -c "
import importlib.metadata as m, torch
v = m.version('omnilingual-asr')
assert v == '0.2.0', f'omnilingual-asr {v}: the v2 cards need 0.2.0'
print('{\"omnilingual-asr\": \"%s\", \"fairseq2\": \"%s\", \"torch\": \"%s\"}' % (v, m.version('fairseq2'), torch.__version__))" || exit 1
  for card in $CARDS; do   # weights download here, on the CPU, with a time limit (not inside a timed GPU run)
    step 1500 "download $card" $OPY -c "
import torch
from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline
ASRInferencePipeline(model_card='$card', device='cpu', dtype=torch.float32)
print('{\"downloaded\": \"$card\"}')" || exit 1
  done
fi

if [ $PHASE = gpu ]; then
  for card in $CARDS; do
    bs=0
    for b in 8 4 2 1; do   # two batches of the longest real clips (~30 s): the worst case of the full pass
      if attempt 600 "$card GPU memory preflight, batch $b" $OPY src/eval_omni.py --model-card $card --device cuda \
           --batch-size $b --longest $((2 * b)) ${SET_ARGS[swivuriso]} --out /tmp/omni_pre_$b; then bs=$b; break; fi
    done
    rm -rf /tmp/omni_pre_*
    if [ $bs = 0 ]; then fails=$((fails + 1)); echo "$card GPU preflight" >> $O/FAILED_PARTS; continue; fi
    echo "=== $card: GPU batch size $bs" | tee -a $O/gpu_batch_sizes.txt
    for set in nchlt fleurs swivuriso soapies; do
      step 1800 "$card GPU: $set" $OPY src/eval_omni.py --model-card $card --device cuda --batch-size $bs \
        --progress-every 400 ${SET_ARGS[$set]} $SEEN --out $O/ctc_$(tag $card)_gpu/eval_$set
    done
  done
fi

if [ $PHASE = cpu ]; then
  end=$(( $(date +%s) + CPU_BUDGET ))
  cpu() {  # cpu <label> <out folder> <args...>: one timed run, inside what is left of the budget
    local label=$1 out=$2; shift 2
    local left=$(( end - $(date +%s) ))
    if [ $left -lt 60 ]; then
      echo "!!! R-0034 $label skipped: CPU time budget used up"; echo "$label (skipped, budget)" >> $O/FAILED_PARTS
      fails=$((fails + 1)); return 1
    fi
    CUDA_VISIBLE_DEVICES="" step $left "$label" $OPY src/eval_omni.py --device cpu --threads 8 --progress-every 10 \
      "$@" $SEEN --out $out
  }
  for card in omniASR_CTC_1B_v2 omniASR_CTC_300M_v2; do   # 1B first: it decides the speed comparison
    for set in nchlt fleurs swivuriso soapies; do
      cpu "$card CPU float32: $set ($CPU_SAMPLE clips)" $O/ctc_$(tag $card)_cpu_float32/eval_$set \
        --model-card $card --dtype float32 --sample $CPU_SAMPLE ${SET_ARGS[$set]}
    done
  done
  for dtype in float32 bfloat16; do   # the bfloat16 probe: 300M only, 20 FLEURS clips, against float32 on the same clips
    cpu "300M CPU $dtype probe: 20 FLEURS clips" $O/ctc_300m_cpu_${dtype}_probe/eval_fleurs \
      --model-card omniASR_CTC_300M_v2 --dtype $dtype --sample 20 ${SET_ARGS[fleurs]}
  done
fi

echo "=== $(date -u +%T) R-0034 $PHASE done, $fails failed part(s)"
[ $fails -eq 0 ]
