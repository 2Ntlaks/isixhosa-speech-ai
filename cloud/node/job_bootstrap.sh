#!/bin/bash
# Runs once at boot on the GPU node (EC2 user-data, Deep Learning Base AMI, Ubuntu 24.04). Filled in by cloud/run_job.sh.
BUCKET="__BUCKET__"; JOB="__JOB__"; MAXMIN="__MAXMIN__"; COMMIT="__COMMIT__"
LOG=/var/log/xhosa-job.log
exec > >(tee -a "$LOG") 2>&1
S3="s3://$BUCKET/jobs/$JOB"
shutdown -h +"$MAXMIN"                       # hard cost cap, whatever happens below
export HOME=/root BUCKET JOB COMMIT HF_HOME=/opt/hf PATH="/root/.local/bin:$PATH" PYTHONUNBUFFERED=1   # progress reaches the log (P-0006)
W=/opt/work; mkdir -p "$W/out" && cd "$W"
log_up() { aws s3 cp "$LOG" "$S3/node.log" --only-show-errors || true; }
finish() { aws s3 sync out "$S3/out/" --only-show-errors; echo "$1" | aws s3 cp - "$S3/$1" || true; log_up; shutdown -h now; exit 0; }
echo "=== $(date -u +%T) node up · $JOB · commit $COMMIT"
command -v aws >/dev/null || { curl -s https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o /tmp/a.zip && cd /tmp && unzip -q a.zip && ./aws/install && cd "$W"; }
( n=0; while sleep 60; do log_up; n=$((n + 1)); [ $((n % 5)) -eq 0 ] && aws s3 sync out "$S3/out/" --only-show-errors; done ) &   # progress + checkpoints to S3 every 5 min
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv

aws s3 cp "$S3/code.tar.gz" . --only-show-errors && tar xzf code.tar.gz || finish FAILED
echo "=== $(date -u +%T) installing Python packages"
curl -LsSf https://astral.sh/uv/0.5.11/install.sh | sh >/dev/null || finish FAILED
uv venv -q -p 3.12 .venv && . .venv/bin/activate && uv pip install -q -r requirements-gpu.txt || finish FAILED
python -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"

echo "=== $(date -u +%T) running runs/$JOB/job.sh"
STATUS=DONE
bash "runs/$JOB/job.sh" || STATUS=FAILED
cp "$LOG" out/node.log
echo "=== $(date -u +%T) finished ($STATUS)"
finish "$STATUS"
