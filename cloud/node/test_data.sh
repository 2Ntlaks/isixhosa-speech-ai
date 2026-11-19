#!/bin/bash
# Fetch data onto a job node, for runs/R-0033, R-0034 and R-0035. Source it from a job.sh (needs $BUCKET):
#   source cloud/node/test_data.sh; get_test_sets      # the four test sets + the training lists for seen/unseen
#   get_fleurs train dev test                          # FLEURS splits (audio extracted)
# FLEURS (P-0021: its S3 copy is gone): taken from S3 datasets/fleurs_xh_za/ if marked COMPLETE there, otherwise
# downloaded from Hugging Face google/fleurs at a pinned revision, checked against the published SHA-256 of each
# archive, and saved back to S3 (same layout as cloud/node/fetch_bootstrap.sh made, plus COMPLETE and MANIFEST.txt).
# The pinned revision gives exactly R-0019's 1034 FLEURS test clips and texts (checked on the laptop, 2026-11-19).
# Downloads go through fetch(): a stalled transfer (< 10 kB/s for 2 min) is aborted and resumed (P-0016), as in
# cloud/node/fetch_bootstrap.sh. An archive already on disk with the right SHA-256 is not fetched again.

export AWS_DEFAULT_REGION=us-east-1   # P-0019: never rely on the node's default region

FLEURS_REV=70bb2e84b976b7e960aa89f1c648e09c59f894dd
declare -A FLEURS_SHA=(
  [train]=48d71a6010d0e72597d1224aaae83604e8aee11ead63ce655bc8c1f96cf76fec
  [dev]=1f28c1f4cdf923ea17b4474130b10b4f8fc451b2d05a28bf6e29d228acbf609a
  [test]=8cb1a3f1ef02d1747980c2df6646d4ee804b1c3de8a314d31fd2786936962be8
)
F=data/fleurs_xh_za
S=data/swivuriso_16k
T=data/nchlt_xho/transcriptions

fetch() {  # url file: resume and retry, abort a stalled transfer; prints the size every 60 s
  echo "--- $(date -u +%T) $2"
  ( while sleep 60; do echo "--- $(date -u +%T) $2: $(du -h "$2" 2>/dev/null | cut -f1) so far"; done ) & local meter=$!
  local rc=1 try; for try in 1 2 3 4 5 6; do
    curl -fL --retry 5 --retry-delay 10 --connect-timeout 30 --speed-limit 10000 --speed-time 120 -C - -sS -o "$2" "$1"       && { rc=0; break; }
    echo "--- $(date -u +%T) $2: stalled or failed (try $try), resuming"; sleep 10; done
  kill $meter 2>/dev/null || true
  return $rc
}

fleurs_ok() { [ -f $F/audio/$1.tar.gz ] && echo "${FLEURS_SHA[$1]}  $F/audio/$1.tar.gz" | sha256sum -c --quiet 2>/dev/null; }

get_fleurs() {  # get_fleurs <split>...
  local SC="s3://$BUCKET/datasets/fleurs_xh_za" H="https://huggingface.co/datasets/google/fleurs/resolve/$FLEURS_REV/data/xh_za"
  mkdir -p $F/audio
  if aws s3 ls "$SC/COMPLETE" >/dev/null 2>&1; then
    echo "=== $(date -u +%T) FLEURS: S3 copy"
    aws s3 cp "$SC/MANIFEST.txt" $F/ --only-show-errors
    for s in train dev test; do aws s3 cp "$SC/$s.tsv" $F/ --only-show-errors; done
    for s in "$@"; do fleurs_ok $s || aws s3 cp "$SC/audio/$s.tar.gz" $F/audio/ --only-show-errors; done
  else
    echo "=== $(date -u +%T) FLEURS: from Hugging Face google/fleurs @ $FLEURS_REV"
    for s in train dev test; do [ -s $F/$s.tsv ] || fetch "$H/$s.tsv" $F/$s.tsv || return 1; done
    for s in "$@"; do fleurs_ok $s || fetch "$H/audio/$s.tar.gz" $F/audio/$s.tar.gz || return 1; done
  fi
  for s in "$@"; do
    fleurs_ok $s || { echo "FLEURS $s.tar.gz checksum mismatch"; return 1; }
    [ -f $F/audio/.extracted_$s ] || { tar xzf $F/audio/$s.tar.gz -C $F/audio/ && touch $F/audio/.extracted_$s; }
  done
  if ! aws s3 ls "$SC/COMPLETE" >/dev/null 2>&1 && [ "$#" -eq 3 ]; then  # all three archives here: restore the S3 copy
    { echo "google/fleurs xh_za @ $FLEURS_REV (CC BY 4.0), fetched $(date -u +%FT%TZ)";
      for s in train dev test; do echo "audio/$s.tar.gz sha256 ${FLEURS_SHA[$s]}"; done; } > $F/MANIFEST.txt
    for s in train dev test; do aws s3 cp $F/$s.tsv "$SC/" --only-show-errors
                                aws s3 cp $F/audio/$s.tar.gz "$SC/audio/" --only-show-errors; done
    aws s3 cp $F/MANIFEST.txt "$SC/" --only-show-errors && date -u +%FT%TZ | aws s3 cp - "$SC/COMPLETE"
    echo "FLEURS saved back to $SC"
  fi
  python - <<'PY'   # the clip list every earlier run scored: 1034 test clips of at most 30 s
import sys; sys.path.insert(0, "src")
import fleurs
n = sum(c["duration"] <= 30 for c in fleurs.load_split("data/fleurs_xh_za/test.tsv", ""))
assert n == 1034, f"FLEURS test has {n} clips <= 30 s, not 1034"
print("FLEURS test: 1034 clips <= 30 s, as in every earlier run")
PY
}

get_test_sets() {
  local D="s3://$BUCKET/datasets/nchlt_xho/extracted/nchlt_xho"
  echo "=== $(date -u +%T) test data"
  aws s3 sync "$D/transcriptions/" $T/ --only-show-errors
  for spk in $(python -c "import sys; sys.path.insert(0, 'src'); import nchlt; print(' '.join(sorted({c['path'].split('/')[-2] for c in nchlt.load_split('$T/nchlt_xho.tst.xml', 'data')})))"); do
    aws s3 sync "$D/audio/$spk/" "data/nchlt_xho/audio/$spk/" --only-show-errors
  done
  get_fleurs test
  aws s3 sync "s3://$BUCKET/datasets/swivuriso_xho_16k/" $S/ --only-show-errors --exclude "*" \
    --include "dev_test.tsv" --include "dev_test/*" --include "summary.json"
  aws s3 sync "s3://$BUCKET/datasets/soapies_engxho/" data/soapies_engxho/ --only-show-errors
  echo "NCHLT test wavs: $(find data/nchlt_xho/audio -name '*.wav' | wc -l); FLEURS test: $(ls $F/audio/test | wc -l);" \
       "Swivuriso dev_test: $(ls $S/dev_test | wc -l); Soapies wavs: $(find data/soapies_engxho -name '*.wav' | wc -l)"
  df -h / | tail -1
}

# The four test sets, as arguments for src/baseline.py, src/eval_guarded.py and src/eval_omni.py
declare -A SET_ARGS=(
  [nchlt]="--xml $T/nchlt_xho.tst.xml --root data"
  [fleurs]="--fleurs-tsv $F/test.tsv --fleurs-audio $F/audio/test"
  [swivuriso]="--swivuriso-tsv $S/dev_test.tsv --swivuriso-audio $S"
  [soapies]="--soapies-root data/soapies_engxho"
)
SEEN="--train-xml $T/nchlt_xho.trn.xml --train-fleurs-tsv $F/train.tsv"   # seen/unseen split, as R-0019's evaluations

setup_ct2() {  # faster-whisper on the job's venv, pinned; the GPU needs cuDNN 9 and cuBLAS 12 from torch's pip wheels
  timeout 900 uv pip install -q faster-whisper==1.2.1 ctranslate2==4.5.0
  local libs
  libs=$(python -c "import nvidia.cublas.lib as b, nvidia.cudnn.lib as c; print(b.__path__[0] + ':' + c.__path__[0])")
  export LD_LIBRARY_PATH="$libs:${LD_LIBRARY_PATH:-}"   # for this venv only: runs/R-0034/omni.sh clears it (F-02)
  python -c "import ctranslate2, faster_whisper; print('faster-whisper', faster_whisper.__version__, 'ctranslate2', ctranslate2.__version__, 'CUDA devices', ctranslate2.get_cuda_device_count())"
}
