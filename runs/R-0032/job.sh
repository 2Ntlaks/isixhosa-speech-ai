#!/bin/bash
# R-0032 on one CPU node (founder's choice B: the laptop is short of memory): Siyamthanda's own end-to-end benchmark
# (bench/bench_e2e.py) on its 100 isiXhosa FLEURS test clips, with each recognizer in turn: Thetha R-0029, R-0019,
# R-0027 (integrations/siyamthanda/), then Meta 1B, the project's current recognizer. The friend's code comes from a
# private S3 copy (s3://$BUCKET/private/siyamthanda-copy/), never from this repo. Same threads as the laptop
# (recognizer 8, NLLB 4), one recognizer at a time.
set -euo pipefail
nproc; free -g | head -2; lscpu | grep "Model name"
C=/opt/siya; mkdir -p $C
aws s3 cp "s3://$BUCKET/private/siyamthanda-copy/R-0032.tar.gz" - --only-show-errors | tar xzf - -C $C
cp integrations/siyamthanda/thetha_engine.py $C/translator/
cp integrations/siyamthanda/bench_thetha.py $C/bench/

echo "=== $(date -u +%T) the project's pinned packages (requirements-meta.txt, minus torch and the Windows/serial extras)"
uv venv -q -p 3.12 /opt/siya-venv
PKGS="faster-whisper==1.2.1 ctranslate2==4.8.2 onnxruntime==1.30.0 transformers==4.57.3 huggingface-hub==0.36.2
      sacrebleu==2.6.0 piper-tts==1.8.0 sentencepiece==0.2.1 soundfile==0.14.0"
VIRTUAL_ENV=/opt/siya-venv uv pip install -q $PKGS || { echo "pinned set failed; unpinned"; VIRTUAL_ENV=/opt/siya-venv uv pip install -q $(echo $PKGS | sed 's/==[^ ]*//g'); }
PY=/opt/siya-venv/bin/python
$PY -c "import importlib.metadata as m; print({p: m.version(p) for p in ['faster-whisper','ctranslate2','onnxruntime','transformers','sacrebleu','piper-tts']})"

for r in R-0029 R-0019 R-0027; do aws s3 sync "s3://$BUCKET/models/$r-int8/" models/$r-int8/ --only-show-errors; done
cd $C
$PY - <<'PY'   # the Meta model at the project's pinned revision, into the HF cache the benchmark reads offline
import sys; sys.path.insert(0, ".")
from huggingface_hub import hf_hub_download
from translator.ctc_asr import ASR_MODELS
s = ASR_MODELS["omni-ctc-1b-v2-int8"]
for f in (s.model_file, s.tokens_file, *s.extra_files):
    print(hf_hub_download(s.repo, f, revision=s.revision))
PY
export HF_HUB_OFFLINE=1
A=(--manifest datasets/zu_xh_test100/manifest.csv --language xh --no-lm)
O=/opt/work/out
for r in R-0029 R-0019 R-0027; do
  echo "=== $(date -u +%T) Thetha $r"
  $PY bench/bench_thetha.py --thetha /opt/work/models/$r-int8 "${A[@]}" --out $O/e2e_xh_thetha-$r.csv 2>&1 | grep -vE '^\s' | tail -n 3
  rm -rf $O/e2e_xh_thetha-$r   # the English WAVs Piper spoke (not needed)
done
echo "=== $(date -u +%T) Meta 1B"
$PY bench/bench_thetha.py "${A[@]}" --out $O/e2e_xh_meta.csv 2>&1 | grep -vE '^\s' | tail -n 3
rm -rf $O/e2e_xh_meta
ls -la $O
