#!/bin/bash
# R-0034 alone (normally it runs inside R-0033's node: runs/R-0033/job.sh). Meta Omnilingual CTC 300M and 1B v2 on
# the four test sets: accuracy on the GPU, then CPU time per clip. Any small GPU node (g6.xlarge is enough).
#   DISK_GB=150 FALLBACK_TYPES="g6.2xlarge" cloud/run_job.sh --run R-0034 --type g6.xlarge --market ondemand --max-hours 2
# Writes straight to out/, so cloud/collect.sh R-0034 puts the results in runs/R-0034/.
set -euo pipefail
export AWS_DEFAULT_REGION=us-east-1
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader; nproc; free -g | head -2
source cloud/node/test_data.sh
get_test_sets
export OMNI_OUT=out
status=0
for phase in setup gpu cpu; do   # in a clean environment (no job-venv library path), each phase time-limited
  env -u LD_LIBRARY_PATH -u VIRTUAL_ENV -u PYTHONPATH timeout 3600 bash runs/R-0034/omni.sh $phase || {
    echo "!!! R-0034 $phase FAILED"; status=1; [ $phase = setup ] && break; }
done
lscpu | grep "Model name" | tee out/cpu.txt
exit $status
