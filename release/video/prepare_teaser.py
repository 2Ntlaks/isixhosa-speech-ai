"""Inputs for the R-0027 teaser (src/Teaser.tsx): the founder's recording -> public/teaser_voice.wav, and src/teaser.json
with when each of his words is spoken (forced alignment, src/swivuriso_long.py), the old and new browser demo outputs on
that recording with each word marked right or wrong, a loudness curve for the orb, and the headline numbers.

  ../../.venv/Scripts/python prepare_teaser.py
Nothing is invented: the transcript is the founder's (his /correct entry, 21 Oct); the outputs come from the demo's own
worker.js in Chrome (R-0028); the numbers are R-0027's Swivuriso test results.
"""
import json
import os
import sys

import jiwer
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src"))
from scoring import normalise  # noqa: E402
from swivuriso_long import aligner_text, word_timings  # noqa: E402

REC = os.path.join(ROOT, "data", "my_voice", "live", "20261021-140009-284018.wav")
SAID = "molweni apho kutwitter ndicela nixhase siphuhlise le model Thetha ukuze ibe luncedo kuluntu lwase south africa"
OUTPUTS = {  # browser demo (transformers.js 3.0.2) on this recording, 22 Oct (R-0028)
    "old": ("R-0007", "molweni apho kuthwita ndicela nixhase siphuhlise leemodelethe tha ukuze ibeluncedo kuluntu lwase south africa"),
    "new": ("R-0027", "molweni apho kuthwita ndicela nixhase siphuhlise le model theatre ukuze ibe luncedo kuluntu lwase south africa"),
}
NUMBERS = {"before": 11.8, "now": 5.1, "what": "letters wrong in every 100, people speaking freely (Swivuriso test)",
           "source": "R-0027 vs R-0007"}

audio, sr = sf.read(REC, dtype="float32")
assert sr == 16000
sf.write(os.path.join(HERE, "public", "teaser_voice.wav"), audio, sr, subtype="PCM_16")

import torch  # noqa: E402
import torchaudio  # noqa: E402
bundle = torchaudio.pipelines.MMS_FA
model = bundle.get_model(with_star=False).eval()
said = normalise(SAID).split()
times = word_timings(model, bundle.get_tokenizer(), bundle.get_aligner(), audio, aligner_text(" ".join(said)), "cpu")


def marked(hyp):
    """Output words with right/wrong and the time they should appear (end of the matching spoken word)."""
    out = jiwer.process_words(" ".join(said), normalise(hyp))
    words, h = [], normalise(hyp).split()
    for c in out.alignments[0]:
        for k in range(c.hyp_start_idx, c.hyp_end_idx):
            ref_k = min(c.ref_start_idx + (k - c.hyp_start_idx), max(c.ref_end_idx - 1, c.ref_start_idx), len(said) - 1)
            words.append({"w": h[k], "ok": c.type == "equal", "t": round(times[ref_k][1], 2)})
    return words, out.substitutions + out.deletions + out.insertions


frame = sr // 30
env = [float(np.sqrt(np.mean(audio[i:i + frame] ** 2))) for i in range(0, len(audio), frame)]
peak = max(env)
data = {"seconds": round(len(audio) / sr, 2), "said": said, "said_times": [[round(a, 2), round(b, 2)] for a, b, _ in times],
        "level": [round(min(1.0, v / peak) ** 0.6, 3) for v in env], "numbers": NUMBERS, "outputs": {}}
for key, (run, hyp) in OUTPUTS.items():
    words, errors = marked(hyp)
    data["outputs"][key] = {"run": run, "words": words, "errors": errors, "of": len(said)}
    print(key, run, f"{errors} errors of {len(said)} words:", " ".join(w["w"] if w["ok"] else w["w"].upper() for w in words))
json.dump(data, open(os.path.join(HERE, "src", "teaser.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("speech", data["said_times"][0][0], "-", data["said_times"][-1][1], "s of", data["seconds"])
