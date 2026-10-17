#!/usr/bin/env bash
# Run one experiment (runs/<RUN-ID>/job.sh) on an AWS GPU node.
#   cloud/run_job.sh --run R-0001 [--max-hours 1] [--type g6.xlarge] [--market spot|ondemand]
# Ships the committed code (git archive of HEAD, so the run maps to an exact commit), starts a self-terminating
# GPU node, which installs requirements-gpu.txt, runs runs/<RUN-ID>/job.sh and uploads ./out to
# s3://<bucket>/jobs/<RUN-ID>/out/. Then: cloud/wait.sh <RUN-ID> and cloud/collect.sh <RUN-ID>.
set -euo pipefail
export AWS_DEFAULT_REGION=us-east-1
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUN=""; MAXH=1; TYPE=g6.xlarge; MARKET=spot
while [ $# -gt 0 ]; do case "$1" in
  --run) RUN=$2;; --max-hours) MAXH=$2;; --type) TYPE=$2;; --market) MARKET=$2;;
  *) echo "unknown arg $1"; exit 1;; esac; shift 2; done
[ -n "$RUN" ] && [ -f "$ROOT/runs/$RUN/job.sh" ] || { echo "need --run with an existing runs/<RUN-ID>/job.sh"; exit 1; }
[ "$MAXH" -le 6 ] || { echo "--max-hours is capped at 6 (cost guard)"; exit 1; }
[ -z "$(git -C "$ROOT" status --porcelain)" ] || { echo "commit first: the run must map to an exact git commit"; exit 1; }
RUNNING=$(aws ec2 describe-instances --filters "Name=tag:project,Values=isixhosa-speech" "Name=tag:kind,Values=gpu" \
  "Name=instance-state-name,Values=pending,running" --query 'Reservations[].Instances[].InstanceId' --output text)
[ -z "$RUNNING" ] || { echo "an isiXhosa GPU node is already running ($RUNNING); one at a time (cost guard)"; exit 1; }

ACCT=$(aws sts get-caller-identity --query Account --output text)
BUCKET="mgaguli-studio-render-$ACCT"; S3="s3://$BUCKET/jobs/$RUN"
TMP="$(mktemp -d)"; P() { cygpath -m "$1" 2>/dev/null || echo "$1"; }
COMMIT=$(git -C "$ROOT" rev-parse --short HEAD)
git -C "$ROOT" archive --format=tar.gz -o "$TMP/code.tar.gz" HEAD
aws s3 cp "$TMP/code.tar.gz" "$S3/code.tar.gz" --only-show-errors
for f in DONE FAILED node.log; do aws s3 rm "$S3/$f" --only-show-errors 2>/dev/null || true; done

sed -e 's/\r$//' -e "s/__BUCKET__/$BUCKET/" -e "s/__JOB__/$RUN/" -e "s/__MAXMIN__/$((MAXH * 60))/" \
    -e "s/__COMMIT__/$COMMIT/" "$ROOT/cloud/node/job_bootstrap.sh" > "$TMP/userdata.sh"
AMI=$(aws ec2 describe-images --owners amazon --filters "Name=name,Values=Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 24.04)*" \
  "Name=state,Values=available" --query 'reverse(sort_by(Images,&CreationDate))[0].ImageId' --output text)
MKT=()
[ "$MARKET" = spot ] && MKT=(--instance-market-options '{"MarketType":"spot","SpotOptions":{"SpotInstanceType":"one-time","InstanceInterruptionBehavior":"terminate"}}')
SUBNETS=$(aws ec2 describe-subnets --filters Name=default-for-az,Values=true --query 'Subnets[].SubnetId' --output text)
ID=""
for T in $TYPE ${FALLBACK_TYPES-g5.xlarge g4dn.xlarge}; do   # other GPU types if short (FALLBACK_TYPES="" = none)
  for SN in $SUBNETS; do                                      # ...and every availability zone
    echo "== trying $T ($MARKET) in $SN"
    ID=$(aws ec2 run-instances --image-id "$AMI" --instance-type "$T" "${MKT[@]}" --subnet-id "$SN" \
      --iam-instance-profile Name=mgaguli-render-node --user-data "file://$(P "$TMP/userdata.sh")" \
      --instance-initiated-shutdown-behavior terminate \
      --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":100,"VolumeType":"gp3","DeleteOnTermination":true}}]' \
      --metadata-options HttpTokens=required,HttpEndpoint=enabled \
      --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=xhosa-$RUN},{Key=project,Value=isixhosa-speech},{Key=kind,Value=gpu}]" \
      --query 'Instances[0].InstanceId' --output text 2>"$TMP/err") && break 2
    grep -qE "InsufficientInstanceCapacity|Unsupported|MaxSpotInstanceCountExceeded" "$TMP/err" || { cat "$TMP/err"; exit 1; }
    ID=""
  done
done
[ -n "$ID" ] || { echo "no GPU capacity anywhere right now ($MARKET)"; exit 1; }
echo "$ID" > "$TMP/id"; aws s3 cp "$TMP/id" "$S3/instance-id" --only-show-errors
echo "== launched $ID ($T, $MARKET) for $RUN at commit $COMMIT; self-terminates after ${MAXH}h at most"
echo "== follow with: cloud/wait.sh $RUN"
