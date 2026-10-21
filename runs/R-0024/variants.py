"""R-0024: why does the founder's "man ukuya" come out as "amanye"? Decode one recording in several altered versions
and list beam 5's five candidates for each. Founder's words (his chat, 21 Oct): "ingxaki ndiyonqena man ukuya
esikolweni namhlanje ..."; the end of the sentence is not known yet, so only "man ukuya" is checked.

  CT2_USE_MKL=0 .venv/Scripts/python runs/R-0024/variants.py
"""
import json
import os
import shutil
import subprocess
import sys

import ctranslate2
import numpy as np
import soundfile as sf
from transformers import WhisperProcessor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))
from scoring import normalise  # noqa: E402

REC = os.path.join(ROOT, "data", "my_voice", "live", "20261021-135703-766246.wav")
OUT = os.path.dirname(os.path.abspath(__file__))
FFMPEG = shutil.which("ffmpeg")


def tempo(x, f):
    """Slow down (f < 1) without changing pitch, via ffmpeg's atempo filter."""
    r = subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-f", "f32le", "-ar", "16000", "-ac", "1", "-i", "pipe:0",
                        "-filter:a", f"atempo={f}", "-f", "f32le", "pipe:1"], input=x.astype(np.float32).tobytes(), capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.float32)


x, sr = sf.read(REC, dtype="float32")
assert sr == 16000
rms = np.sqrt(np.mean(x ** 2))
variants = {
    "original": x,
    "louder (-20 dBFS)": x * (10 ** (-20 / 20) / rms),
    "slowed 0.9x": tempo(x, 0.9),
    "slowed 0.8x": tempo(x, 0.8),
    "first 4.0 s": x[:64000],
    "first 3.0 s": x[:48000],
    "0.5 s silence before": np.concatenate([np.zeros(8000, np.float32), x]),
}

results = {"recording": os.path.basename(REC), "founder_words_checked": "man ukuya", "beam_size": 5, "models": {}}
for name in ["R-0019-int8", "R-0012-int8"]:
    path = os.path.join(ROOT, "data", "models", name)
    proc = WhisperProcessor.from_pretrained(path)
    m = ctranslate2.models.Whisper(path, device="cpu", compute_type="int8", intra_threads=8)
    prompt = proc.tokenizer.convert_tokens_to_ids(["<|startoftranscript|>", "<|sw|>", "<|transcribe|>", "<|notimestamps|>"])
    results["models"][name] = {}
    for v, audio in variants.items():
        feats = proc([audio], sampling_rate=16000, return_tensors="np").input_features
        r = m.generate(ctranslate2.StorageView.from_array(np.ascontiguousarray(feats)), [prompt], beam_size=5,
                       num_hypotheses=5, max_length=225)
        cands = [proc.tokenizer.decode(s, skip_special_tokens=True).strip() for s in r[0].sequences_ids]
        results["models"][name][v] = {"top_has_man_ukuya": "man ukuya" in normalise(cands[0]),
                                      "any_has_man_ukuya": any("man ukuya" in normalise(c) for c in cands),
                                      "any_has_ukuya": any("ukuya" in normalise(c).split() for c in cands),
                                      "candidates": cands}
        print(name, v, "|", cands[0], flush=True)
    del m
json.dump(results, open(os.path.join(OUT, "variants.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
