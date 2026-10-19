"""Prepare the video's inputs: FLEURS clips -> public/, real model outputs + waveform + speech span -> src/data.json,
and synthesised sound effects -> public/. Nothing here is invented: every transcript comes from a run record.

  ../../.venv/Scripts/python prepare.py
Audio: Google FLEURS xh_za test (CC BY 4.0), extracted to data/video/test/ from the project's S3 copy.
"""
import json
import os

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SR = 16000


def preds(path):
    return {o["id"]: o for o in map(json.loads, open(os.path.join(ROOT, path), encoding="utf-8"))}


r12 = preds("runs/R-0012/eval_fleurs/predictions.jsonl")
r11 = preds("runs/R-0011/eval_fleurs/predictions.jsonl")  # stock whisper-medium, <|sw|> forced
r06 = preds("runs/R-0006/predictions.jsonl")              # stock whisper-small, <|sw|> forced

CLIPS = [  # (name, FLEURS id, which stock run to show)
    ("loop", "17388926234373433928", ("stock whisper-small", r06)),
    ("train", "12018871727411808101", ("stock whisper-medium", r11)),
    ("east", "16752887379644933070", ("stock whisper-medium", r11)),
]

data = {"clips": {}}
for name, fid, (stock_name, stock) in CLIPS:
    key = "fleurs_" + fid
    audio, sr = sf.read(os.path.join(ROOT, "data", "video", "test", fid + ".wav"), dtype="float32")
    assert sr == SR
    peak = np.abs(audio).max()
    audio = (audio / peak * 0.9).astype("float32")  # even loudness across clips
    sf.write(os.path.join(HERE, "public", name + ".wav"), audio, SR, subtype="PCM_16")
    # 20 ms frames: loudness bars for the waveform, and where speech starts and stops
    hop = SR // 50
    rms = np.array([np.sqrt(np.mean(audio[i:i + hop] ** 2)) for i in range(0, len(audio) - hop, hop)])
    voiced = np.where(rms > rms.max() * 0.08)[0]
    bars = [round(float(x), 3) for x in (rms / rms.max())]
    data["clips"][name] = {
        "fleurs_id": fid, "seconds": round(len(audio) / SR, 2),
        "speech_start": round(voiced[0] * hop / SR, 2), "speech_end": round((voiced[-1] + 1) * hop / SR, 2),
        "bars": bars, "said": r12[key]["text"], "r0012": r12[key]["hyp"].strip(),
        "stock_name": stock_name, "stock": stock[key]["hyp"].strip(),
    }
    print(name, data["clips"][name]["seconds"], "s | R-0012 exact:",
          data["clips"][name]["r0012"].lower() == data["clips"][name]["said"].lower())

# numbers shown in the video, each from a run (results.md)
data["numbers"] = {"stock_small_fleurs_cer": 65.45, "r0012_fleurs_cer": 8.03, "cost_usd": 10,
                   "hours_of_speech": 64, "browser_mb": 300, "thetha_exact": [10, 12]}
json.dump(data, open(os.path.join(HERE, "src", "data.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# sound design, synthesised here (no licences involved): a soft key tick, a whoosh, a low warm bed
rng = np.random.default_rng(7)
t = np.arange(int(0.05 * 44100)) / 44100
tick = (rng.standard_normal(t.size) * np.exp(-t * 160) * 0.25 + np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 220) * 0.15)
sf.write(os.path.join(HERE, "public", "tick.wav"), tick.astype("float32"), 44100, subtype="PCM_16")
t = np.arange(int(0.9 * 44100)) / 44100
env = np.sin(np.pi * t / t[-1]) ** 2
noise = np.convolve(rng.standard_normal(t.size), np.ones(40) / 40, mode="same")
sf.write(os.path.join(HERE, "public", "whoosh.wav"), (noise * env * 0.5).astype("float32"), 44100, subtype="PCM_16")
t = np.arange(int(40 * 44100)) / 44100
bed = sum(np.sin(2 * np.pi * f * t + p) * a for f, p, a in [(55, 0, .5), (82.4, 1, .3), (110, 2, .15), (164.8, .5, .08)])
bed *= (0.75 + 0.25 * np.sin(2 * np.pi * t / 9)) * 0.12
fade = np.minimum(1, np.minimum(t / 2, (t[-1] - t) / 3))
sf.write(os.path.join(HERE, "public", "bed.wav"), (bed * fade).astype("float32"), 44100, subtype="PCM_16")
print("sound design written")
