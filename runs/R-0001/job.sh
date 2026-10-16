#!/bin/bash
# R-0001: stock whisper-small on the full NCHLT isiXhosa test set, language auto-detected. Runs on the GPU node.
set -euo pipefail
D="s3://$BUCKET/datasets/nchlt_xho/extracted/nchlt_xho"
aws s3 sync "$D/transcriptions/" data/nchlt_xho/transcriptions/ --only-show-errors
for s in 500 501 502 503 504 505 506 507; do   # the 8 held-out test speakers
  aws s3 sync "$D/audio/$s/" "data/nchlt_xho/audio/$s/" --only-show-errors
done
echo "test audio: $(find data/nchlt_xho/audio -name '*.wav' | wc -l) wav files"
python src/baseline.py --xml data/nchlt_xho/transcriptions/nchlt_xho.tst.xml --root data --out out \
  --model openai/whisper-small --language auto --batch-size 32 2>&1 | grep -v "^\s*$" | tee out/baseline.log
