#!/usr/bin/env bash
# Copy a finished run's outputs from S3 into runs/<RUN-ID>/ (files over 5 MB stay in S3; their paths are listed).
#   cloud/collect.sh R-0001
set -euo pipefail
export AWS_DEFAULT_REGION=us-east-1
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; RUN=$1
ACCT=$(aws sts get-caller-identity --query Account --output text)
S3="s3://mgaguli-studio-render-$ACCT/jobs/$RUN/out"
aws s3 ls "$S3/" --recursive | while read -r d t size key; do
  f="${key#jobs/$RUN/out/}"
  if [ "$size" -le 5000000 ]; then aws s3 cp "s3://mgaguli-studio-render-$ACCT/$key" "$ROOT/runs/$RUN/$f" --only-show-errors
  else echo "kept in S3 ($((size / 1000000)) MB): s3://mgaguli-studio-render-$ACCT/$key"; fi
done
ls -la "$ROOT/runs/$RUN"
