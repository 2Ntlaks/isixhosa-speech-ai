#!/usr/bin/env bash
# Follow a cloud job until it finishes.   cloud/wait.sh <job> [poll_seconds]
set -uo pipefail
export AWS_DEFAULT_REGION=us-east-1
JOB=$1; POLL=${2:-60}
ACCT=$(aws sts get-caller-identity --query Account --output text)
S3="s3://mgaguli-studio-render-$ACCT/jobs/$JOB"
ID=$(aws s3 cp "$S3/instance-id" - 2>/dev/null)
while true; do
  STATE=$(aws ec2 describe-instances --instance-ids "$ID" --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null)
  LAST=$(aws s3 cp "$S3/node.log" - 2>/dev/null | grep -E "^(===|---)" | tail -1)
  echo "$(date +%T) $JOB: node $ID $STATE · $LAST"
  if aws s3 ls "$S3/DONE" >/dev/null 2>&1; then echo "DONE"; break; fi
  if aws s3 ls "$S3/FAILED" >/dev/null 2>&1; then echo "FAILED (see: aws s3 cp $S3/node.log -)"; exit 1; fi
  if [ "$STATE" = terminated ] || [ "$STATE" = shutting-down ]; then
    echo "node stopped before DONE (time cap?). Check: aws s3 cp $S3/node.log -"; exit 1; fi
  sleep "$POLL"
done
