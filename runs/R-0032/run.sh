#!/bin/bash
# R-0032: Siyamthanda's end-to-end benchmark on a COPY of the project, isiXhosa test clips, one recognizer at a time.
# Uses the project's own .venv-meta interpreter (read-only: no bytecode written, offline) from the copy folder.
set -euo pipefail
R="C:/Users/ntlak/Downloads/isiXhosa Speech AI"
C="C:/Users/ntlak/Downloads/siyamthanda-thetha-test"
PY="C:/Users/ntlak/OneDrive/Documents/Siyamthanda Project/.venv-meta/Scripts/python.exe"
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1
cp "$R/integrations/siyamthanda/thetha_engine.py" "$C/translator/"
cp "$R/integrations/siyamthanda/bench_thetha.py" "$C/bench/"
cd "$C"
A=(--manifest datasets/zu_xh_test100/manifest.csv --language xh --no-lm)
for m in R-0029 R-0019 R-0027; do
  echo "=== $(date +%T) Thetha $m"
  "$PY" bench/bench_thetha.py --thetha "$R/data/models/$m-int8" "${A[@]}" --out logs/e2e_test100_xh_thetha-$m.csv > logs/thetha-$m.log 2>&1
done
echo "=== $(date +%T) Meta 1B (the project's current recognizer), same session"
"$PY" bench/bench_thetha.py "${A[@]}" --out logs/e2e_test100_xh_meta-rerun.csv > logs/meta-rerun.log 2>&1
echo "=== $(date +%T) done"
