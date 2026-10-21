#!/usr/bin/env bash
# Download the speech datasets on a small cloud machine, straight into the private S3 bucket (decision D-0004).
#   cloud/fetch_data.sh --job fetch-1 --datasets fleurs,nchlt [--max-hours 2]
# Then: cloud/wait.sh fetch-1
# Lands in s3://<bucket>/datasets/<name>/ with a MANIFEST.txt (sizes, checksums, sources). Datasets already
# marked COMPLETE in S3 are skipped, so re-running is safe. The machine has no GPU (~$0.02/h) and terminates itself.
set -euo pipefail
export AWS_DEFAULT_REGION=us-east-1
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
JOB=""; DATASETS=""; MAXH=2; TYPE=t3.small; DISK=40
while [ $# -gt 0 ]; do case "$1" in
  --job) JOB=$2;; --datasets) DATASETS=$2;; --max-hours) MAXH=$2;; --type) TYPE=$2;; --disk) DISK=$2;;
  *) echo "unknown arg $1"; exit 1;; esac; shift 2; done
[ -n "$JOB" ] && [ -n "$DATASETS" ] || {
  echo "need --job and --datasets (fleurs,nchlt,nchlt_eng,soapies,nchlt_aux,swivuriso)"; exit 1; }
[ "$DISK" -le 100 ] || { echo "--disk is capped at 100 GB"; exit 1; }
[ "$MAXH" -le 3 ] || { echo "--max-hours is capped at 3 for downloads (cost guard)"; exit 1; }
case "$TYPE" in g*|p*) echo "downloads don't need a GPU"; exit 1;; esac

ACCT=$(aws sts get-caller-identity --query Account --output text)
BUCKET="mgaguli-studio-render-$ACCT"; S3="s3://$BUCKET/jobs/$JOB"
TMP="$(mktemp -d)"; P() { cygpath -m "$1" 2>/dev/null || echo "$1"; }
aws s3 rm "$S3/DONE" --only-show-errors 2>/dev/null || true
aws s3 rm "$S3/FAILED" --only-show-errors 2>/dev/null || true
ID=""
cleanup() {  # the token never outlives a launch that did not happen (PR #1 review)
  rm -f "$TMP/hf_token"
  [ -n "$ID" ] || aws s3 rm "$S3/hf_token" --only-show-errors 2>/dev/null || true
}
trap cleanup EXIT
if [[ ",$DATASETS," == *,swivuriso,* ]]; then  # gated on Hugging Face: file list, pinned revision and token for the node
  if aws s3 ls "s3://$BUCKET/datasets/swivuriso_xho/COMPLETE" >/dev/null 2>&1; then
    echo "== swivuriso is already complete in S3: no token sent"
  else
    "$ROOT/.venv/Scripts/python" "$ROOT/cloud/swivuriso_files.py" "$(P "$TMP")" || exit 1
    for f in files.tsv revision.txt hf_token; do aws s3 cp "$(P "$TMP/$f")" "$S3/$f" --only-show-errors; done
    rm -f "$TMP/hf_token"
  fi
fi

sed -e 's/\r$//' -e "s/__BUCKET__/$BUCKET/" -e "s/__JOB__/$JOB/" -e "s/__MAXMIN__/$((MAXH * 60))/" \
    -e "s/__DATASETS__/$DATASETS/" "$ROOT/cloud/node/fetch_bootstrap.sh" > "$TMP/userdata.sh"
AMI=$(aws ec2 describe-images --owners amazon --filters "Name=name,Values=al2023-ami-2023.*-kernel-6.*-x86_64" \
  "Name=state,Values=available" --query 'reverse(sort_by(Images,&CreationDate))[0].ImageId' --output text)
ID=$(aws ec2 run-instances --image-id "$AMI" --instance-type "$TYPE" \
  --iam-instance-profile Name=mgaguli-render-node --user-data "file://$(P "$TMP/userdata.sh")" \
  --instance-initiated-shutdown-behavior terminate \
  --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":'"$DISK"',"VolumeType":"gp3","DeleteOnTermination":true}}]' \
  --metadata-options HttpTokens=required,HttpEndpoint=enabled \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=xhosa-$JOB},{Key=project,Value=isixhosa-speech}]" \
  --query 'Instances[0].InstanceId' --output text)
echo "$ID" > "$TMP/id"; aws s3 cp "$TMP/id" "$S3/instance-id" --only-show-errors
echo "== launched $ID ($TYPE, job $JOB, datasets: $DATASETS), self-terminates after ${MAXH}h at most"
echo "== follow with: cloud/wait.sh $JOB"
