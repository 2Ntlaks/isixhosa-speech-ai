#!/bin/bash
# R-0031 on one CPU node (no GPU needed): the fast int8 copy of R-0029, checked the way the laptop and the Siyamthanda
# hub run it (CTranslate2 int8 on CPU), so the founder's laptop only ever downloads the 0.75 GB copy.
#   1. R-0029 and R-0019 -> CTranslate2 int8 (+ tokenizer.json, which faster-whisper needs); copies to S3 models/<run>-int8/
#   2. R-0020-style check: R-0029-int8 vs its own GPU outputs on 200 unseen-sentence NCHLT test clips
#   3. Soapies mixed isiXhosa-English test (R-0030's settings) on R-0029-int8 and, on the same node, R-0019-int8
# The three scoring jobs run side by side, 10 threads each.
set -euo pipefail
export CT2_USE_MKL=0
uv pip install -q ctranslate2==4.5.0
nproc; free -g | head -2

for r in R-0029 R-0019; do
  aws s3 sync "s3://$BUCKET/models/$r/" models/$r/ --only-show-errors --exclude training_args.bin
  ct2-transformers-converter --model models/$r --output_dir models/$r-int8 --quantization int8 2>&1 | tail -2
  python -c "import sys; from transformers import WhisperTokenizerFast as T; T.from_pretrained(sys.argv[1]).backend_tokenizer.save(sys.argv[2] + '/tokenizer.json')" models/$r models/$r-int8
  rm -rf models/$r
  du -sh models/$r-int8; ls models/$r-int8
  aws s3 sync models/$r-int8/ "s3://$BUCKET/models/$r-int8/" --only-show-errors
done

aws s3 sync "s3://$BUCKET/datasets/soapies_engxho/" data/soapies_engxho/ --only-show-errors
D="s3://$BUCKET/datasets/nchlt_xho/extracted/nchlt_xho"
for s in $(python -c "import json; print(' '.join(sorted({json.loads(l)['id'].split('_')[2][:3] for l in open('runs/R-0029/eval_nchlt/predictions.jsonl')})))"); do
  aws s3 sync "$D/audio/$s/" "data/nchlt_xho/audio/$s/" --only-show-errors
done

echo "=== $(date -u +%T) scoring (3 jobs side by side)"
python src/eval_ct2.py --model models/R-0029-int8 --reference runs/R-0029/eval_nchlt/predictions.jsonl \
  --sample unseen:200 --threads 10 --out out/nchlt_check > out/nchlt_check.log 2>&1 &
for r in R-0029 R-0019; do
  python src/eval_soapies.py --model models/$r-int8 --lang sw --threads 10 --out out/soapies_$r > out/soapies_$r.log 2>&1 &
done
wait
tail -1 out/nchlt_check.log out/soapies_*.log
