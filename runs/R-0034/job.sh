#!/bin/bash
# R-0034 alone (normally it runs inside R-0033's node: runs/R-0033/job.sh). Meta Omnilingual CTC 300M and 1B v2 on
# the four test sets: accuracy on the GPU, then CPU time per clip. Any small GPU node (g6.xlarge is enough).
#   FALLBACK_TYPES="g6.2xlarge" cloud/run_job.sh --run R-0034 --type g6.xlarge --market ondemand --max-hours 2
set -euo pipefail
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader; nproc; free -g | head -2
source cloud/node/test_data.sh
get_test_sets
for phase in setup gpu cpu; do bash runs/R-0034/omni.sh $phase; done
lscpu | grep "Model name" | tee out/R-0034/cpu.txt
