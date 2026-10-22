"""Run Siyamthanda's own end-to-end benchmark (bench/bench_e2e.py, unchanged) with Thetha as the recognizer.

Run from the copy, with the copy's interpreter environment:
  python bench/bench_thetha.py --thetha <int8 model dir> [--beam 1] --manifest datasets/zu_xh_test100/manifest.csv \
      --language xh --no-lm --out logs/e2e_test100_xh_thetha-R-0029.csv
Without --thetha it runs bench_e2e.py exactly as before (the Meta recognizer). With it, the benchmark's MetaTranslator
is swapped for ThethaTranslator and a Thetha entry is added to the recognizer list, so the summary records which model
ran; everything else (clips, scoring, NLLB, Piper, timing scope) is the benchmark's own code.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bench"))

import bench_e2e  # noqa: E402
from translator.ctc_asr import ASR_MODELS, AsrModelSpec  # noqa: E402
from translator.thetha_engine import ThethaTranslator  # noqa: E402


def take(flag: str, default: str | None = None) -> str | None:
    if flag not in sys.argv:
        return default
    i = sys.argv.index(flag)
    value = sys.argv[i + 1]
    del sys.argv[i:i + 2]
    return value


model_dir = take("--thetha")
beam = int(take("--beam", "1"))
if model_dir:
    model_dir = Path(model_dir).resolve()
    name = f"thetha-{model_dir.name}-beam{beam}"
    ASR_MODELS[name] = AsrModelSpec(str(model_dir), model_dir.name, "model.bin", "tokenizer.json")
    sys.argv += ["--asr-model", name]

    def make(cpu_threads, *, mt_backend, mt_beam_size, asr_model, mt_model, af_lm, restore, truecase, asr_threads):
        return ThethaTranslator(model_dir, cpu_threads, asr_threads=asr_threads, beam_size=beam,
                                mt_backend=mt_backend, mt_beam_size=mt_beam_size, mt_model=mt_model, restore=restore)

    bench_e2e.MetaTranslator = make

raise SystemExit(bench_e2e.main())
