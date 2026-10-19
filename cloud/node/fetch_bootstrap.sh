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

md5ok() {  # file expected_md5
  local m; m=$(md5sum "$1" | cut -d' ' -f1)
  [ "$m" = "$2" ] || { echo "MD5 mismatch for $1: $m (SADiLaR lists $2)"; return 1; }
  echo "MD5 of $1 matches SADiLaR's published checksum"
}

nchlt_eng() {  # NCHLT English Speech Corpus, CC BY 3.0, SADiLaR handle 20.500.12185/274 (stage 4, D-0016)
  done_already nchlt_eng && return 0
  mkdir -p "$W/nchlt_eng" && cd "$W/nchlt_eng" && : > MANIFEST.txt
  get https://repo.sadilar.org/server/api/core/bitstreams/b18e11bc-7b45-4685-a584-1cead35fe347/content \
      nchlt.speech.corpus.eng_1.zip || return 1
  md5ok nchlt.speech.corpus.eng_1.zip fafafce8ff4700f9491bd1bf123a419f || return 1
  unzip -q nchlt.speech.corpus.eng_1.zip -d extracted || return 1
  find extracted -maxdepth 3 | head -20
  publish nchlt_eng
}

soapies() {  # Soap opera code-switched speech, English-isiXhosa set, RESEARCH ONLY, handle 20.500.12185/545.
  # Test/dev use only, never training a published model, never re-hosted (D-0016).
  done_already soapies_engxho && return 0
  mkdir -p "$W/soapies_engxho" && cd "$W/soapies_engxho" && : > MANIFEST.txt
  local B=https://repo.sadilar.org/server/api/core/bitstreams
  get $B/3320889f-5587-4da1-8340-7947b237fd54/content balanced_engxho.zip || return 1
  get $B/0940a339-fadc-4246-bed2-3806f3322c76/content balanced_engxho.xml || return 1
  get $B/60c781ad-2cd5-4003-bc78-76f1c960a6fa/content soapies_dev_and_test_set_utterance_ids.zip || return 1
  get $B/2db1e48b-6f8f-4aff-b35f-b0718c6f5740/content README_data.txt || return 1
  get $B/06253570-ccbd-4240-ac23-e7a2b5c37ec8/content license.txt || return 1
  md5ok balanced_engxho.zip ba6d3ca27a169f32f42bcb55b7e99005 || return 1
  md5ok balanced_engxho.xml d6fd7c59880ae411304d20f266e9a977 || return 1
  md5ok soapies_dev_and_test_set_utterance_ids.zip df8b9fdd4a2e1c4680face3847ad752f || return 1
  unzip -q balanced_engxho.zip -d extracted && unzip -q soapies_dev_and_test_set_utterance_ids.zip -d ids || return 1
  find extracted ids -maxdepth 3 | head -20
  publish soapies_engxho
}

STATUS=DONE
IFS=',' read -ra LIST <<< "$DATASETS"
for d in "${LIST[@]}"; do
  echo "=== $(date -u +%T) dataset: $d"
  case "$d" in fleurs|nchlt|nchlt_eng|soapies) "$d" || { echo "=== $d FAILED"; STATUS=FAILED; } ;;
    *) echo "unknown dataset $d"; STATUS=FAILED ;; esac
  cd "$W"
done
echo "=== $(date -u +%T) all done ($STATUS)"
finish "$STATUS"
