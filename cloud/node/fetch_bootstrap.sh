#!/bin/bash
# Runs once at boot on the download machine (EC2 user-data, Amazon Linux 2023). Placeholders filled by cloud/fetch_data.sh.
BUCKET="__BUCKET__"; JOB="__JOB__"; MAXMIN="__MAXMIN__"; DATASETS="__DATASETS__"
LOG=/var/log/xhosa-fetch.log
exec > >(tee -a "$LOG") 2>&1
S3="s3://$BUCKET/jobs/$JOB"; DS="s3://$BUCKET/datasets"
shutdown -h +"$MAXMIN"                       # hard cost cap, whatever happens below
log_up() { aws s3 cp "$LOG" "$S3/node.log" --only-show-errors || true; }
finish() { echo "$1" | aws s3 cp - "$S3/$1" || true; log_up; shutdown -h now; exit 0; }
echo "=== $(date -u +%T) node up"
dnf install -yq unzip >/dev/null || finish FAILED
W=/data; mkdir -p "$W" && cd "$W"
( while sleep 60; do log_up; done ) &

get() {  # url file -> downloads with resume and retries, then adds a manifest line
  echo "--- $(date -u +%T) $2"
  ( while sleep 60; do echo "--- $(date -u +%T) $2: $(du -h "$2" 2>/dev/null | cut -f1) so far"; done ) & local meter=$!
  curl -fL --retry 5 --retry-delay 10 -C - -sS -o "$2" "$1"; local rc=$?
  kill $meter; [ $rc -eq 0 ] || return 1
  printf "%s  %s  %s  %s\n" "$(stat -c %s "$2")" "$(sha256sum "$2" | cut -d' ' -f1)" "$2" "$1" >> MANIFEST.txt
}
done_already() { aws s3 ls "$DS/$1/COMPLETE" >/dev/null 2>&1 && echo "=== $1 already complete in S3, skipping"; }
publish() {  # name: upload the folder, then mark it complete
  { echo "# $1 · fetched $(date -u +%F) by job $JOB"; echo "# bytes  sha256  file  source"; cat MANIFEST.txt; } > M && mv M MANIFEST.txt
  aws s3 sync . "$DS/$1/" --only-show-errors --exclude "*.zip" || return 1   # zip itself: checksum kept in the manifest
  date -u +%FT%TZ | aws s3 cp - "$DS/$1/COMPLETE"
  echo "=== $(date -u +%T) $1 uploaded: $(du -sh . | cut -f1), $(find . -type f | wc -l) files"
}

fleurs() {  # Google FLEURS isiXhosa (xh_za), CC BY 4.0, public on Hugging Face
  done_already fleurs_xh_za && return 0
  mkdir -p "$W/fleurs_xh_za/audio" && cd "$W/fleurs_xh_za" && : > MANIFEST.txt
  local H=https://huggingface.co/datasets/google/fleurs/resolve/main/data/xh_za
  for s in train dev test; do
    get "$H/$s.tsv" "$s.tsv" && get "$H/audio/$s.tar.gz" "audio/$s.tar.gz" || return 1
    gzip -t "audio/$s.tar.gz" || { echo "corrupt archive audio/$s.tar.gz"; return 1; }
  done
  publish fleurs_xh_za
}

nchlt() {  # NCHLT isiXhosa Speech Corpus, CC BY 3.0, SADiLaR handle 20.500.12185/279
  done_already nchlt_xho && return 0
  mkdir -p "$W/nchlt_xho" && cd "$W/nchlt_xho" && : > MANIFEST.txt
  get https://repo.sadilar.org/server/api/core/bitstreams/9e5423b8-1482-4e58-a588-1062bd7914e8/content \
      nchlt.speech.corpus.xho.zip || return 1
  local md5; md5=$(md5sum nchlt.speech.corpus.xho.zip | cut -d' ' -f1)
  [ "$md5" = 0e8918da0e1ac9acb3a300c7198c33dd ] || { echo "MD5 mismatch: $md5 (SADiLaR lists 0e8918da...)"; return 1; }
  echo "MD5 matches SADiLaR's published checksum"
  unzip -q nchlt.speech.corpus.xho.zip -d extracted || return 1
  find extracted -maxdepth 3 | head -20
  publish nchlt_xho
}

STATUS=DONE
IFS=',' read -ra LIST <<< "$DATASETS"
for d in "${LIST[@]}"; do
  echo "=== $(date -u +%T) dataset: $d"
  case "$d" in fleurs|nchlt) "$d" || { echo "=== $d FAILED"; STATUS=FAILED; } ;;
    *) echo "unknown dataset $d"; STATUS=FAILED ;; esac
  cd "$W"
done
echo "=== $(date -u +%T) all done ($STATUS)"
finish "$STATUS"
