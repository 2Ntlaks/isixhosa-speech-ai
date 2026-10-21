"""R-0026: where does Thetha's time go on the laptop CPU, and which settings make it faster without changing answers?

  CT2_USE_MKL=0 .venv/Scripts/python runs/R-0026/speed.py split          # features vs encoder vs decoder
  CT2_USE_MKL=0 .venv/Scripts/python runs/R-0026/speed.py threads        # encoder time at 4/6/8/12/16 threads
  CT2_USE_MKL=0 .venv/Scripts/python runs/R-0026/speed.py context        # shorter encoder window (audio_ctx), accuracy cost
  CT2_USE_MKL=0 .venv/Scripts/python runs/R-0026/speed.py validate       # 300 clips: now vs guards vs guards + short window
Clips: the 32 seed-22 clips of R-0025 (NCHLT test, from R-0021's sample). Writes <mode>.json next to this file.
No transcripts in the output files, only scores and timings.
"""
import json
import os
import random
import statistics
import sys
import time

import ctranslate2
import numpy as np
import soundfile as sf
from transformers import WhisperProcessor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))
from scoring import normalise, score  # noqa: E402

MODEL = os.path.join(ROOT, "data", "models", "R-0019-int8")
mode = sys.argv[1]
rows = [json.loads(l) for l in open(os.path.join(ROOT, "runs", "R-0021", "predictions.jsonl"), encoding="utf-8")]
rows = sorted(random.Random(22).sample(rows, 32), key=lambda r: r["id"])
audios = [sf.read(os.path.join(ROOT, "data", "nchlt_xho", "audio", r["id"].split("_")[2][:3], r["id"] + ".wav"), dtype="float32")[0]
          for r in rows]
proc = WhisperProcessor.from_pretrained(MODEL)
PROMPT = proc.tokenizer.convert_tokens_to_ids(["<|startoftranscript|>", "<|sw|>", "<|transcribe|>", "<|notimestamps|>"])


def feats_of(audio):
    return proc([audio], sampling_rate=16000, return_tensors="np").input_features


def sv(x):
    return ctranslate2.StorageView.from_array(np.ascontiguousarray(x))


def text(res):
    return proc.tokenizer.decode(res[0].sequences_ids[0], skip_special_tokens=True).strip()


out = {"mode": mode, "clips": len(rows), "mean_audio_seconds": round(statistics.mean(len(a) / 16000 for a in audios), 2),
       "ctranslate2": ctranslate2.__version__, "mkl": os.environ.get("CT2_USE_MKL", "default")}

if mode == "split":
    m = ctranslate2.models.Whisper(MODEL, device="cpu", compute_type="int8", intra_threads=8)
    m.generate(sv(feats_of(audios[0])), [PROMPT], beam_size=5)  # warm-up
    t = {"features": [], "encoder": [], "decode_beam5": [], "decode_greedy": [], "generate_beam5_total": []}
    for a in audios:
        s = time.perf_counter(); f = feats_of(a); t["features"].append(time.perf_counter() - s)
        s = time.perf_counter(); enc = m.encode(sv(f)); t["encoder"].append(time.perf_counter() - s)
        s = time.perf_counter(); m.generate(enc, [PROMPT], beam_size=5); t["decode_beam5"].append(time.perf_counter() - s)
        s = time.perf_counter(); m.generate(enc, [PROMPT], beam_size=1); t["decode_greedy"].append(time.perf_counter() - s)
        s = time.perf_counter(); m.generate(sv(f), [PROMPT], beam_size=5); t["generate_beam5_total"].append(time.perf_counter() - s)
    out["mean_seconds"] = {k: round(statistics.mean(v), 3) for k, v in t.items()}

elif mode == "threads":
    feats = [sv(feats_of(a)) for a in audios[:8]]
    out["encoder_mean_seconds"] = {}
    for n in [4, 6, 8, 12, 16]:
        m = ctranslate2.models.Whisper(MODEL, device="cpu", compute_type="int8", intra_threads=n)
        m.encode(feats[0])
        s = time.perf_counter()
        for f in feats:
            m.encode(f)
        out["encoder_mean_seconds"][n] = round((time.perf_counter() - s) / len(feats), 3)
        print(n, out["encoder_mean_seconds"][n], flush=True)
        del m

elif mode == "context":
    # Whisper always encodes a 30 s window (3000 frames -> 1500 positions). A shorter window is much less encoder
    # work, but R-0019 never saw one in training, so accuracy may drop. Window = audio length + margin, rounded up.
    m = ctranslate2.models.Whisper(MODEL, device="cpu", compute_type="int8", intra_threads=8)
    out["settings"] = {}
    for margin in [None, 2.0, 1.0]:
        hyps, secs = [], 0.0
        for a in audios:
            f = feats_of(a)
            if margin is not None:
                frames = min(3000, int(np.ceil((len(a) / 16000 + margin) * 100 / 2) * 2))
                f = f[:, :, :frames]
            s = time.perf_counter()
            hyps.append(text(m.generate(sv(f), [PROMPT], beam_size=5, max_length=96)))
            secs += time.perf_counter() - s
        full = out["settings"].get("full 30 s", {}).get("hyps")
        key = "full 30 s" if margin is None else f"audio + {margin} s"
        sc = score([r["text"] for r in rows], hyps)
        out["settings"][key] = {"wer": round(sc["wer"], 2), "cer": round(sc["cer"], 2), "mean_seconds": round(secs / len(rows), 3),
                                "hyps": hyps}
        if full:
            out["settings"][key]["same_as_full"] = sum(normalise(x) == normalise(y) for x, y in zip(hyps, full))
        print(key, {k: v for k, v in out["settings"][key].items() if k != "hyps"}, flush=True)
    for v in out["settings"].values():
        v.pop("hyps")

elif mode == "validate":
    # Larger check of the 32-clip finding: 200 NCHLT test clips (R-0021's sample) + 100 NCHLT dev clips (R-0022).
    # Settings: "now" = the live page (30 s window, beam 5, limit 225); "guards" = same plus an output cap tied to the
    # audio length, repetition_penalty 1.1 and no_repeat_ngram_size 4; "fast" = guards + window of max(10 s, audio + 1 s).
    sets = {"nchlt_test_200": [(r["id"], r["text"]) for r in (json.loads(l) for l in open(os.path.join(ROOT, "runs", "R-0021", "predictions.jsonl"), encoding="utf-8"))],
            "nchlt_dev_100": [(r["id"], r["text"]) for r in (json.loads(l) for l in open(os.path.join(ROOT, "runs", "R-0022", "clips.jsonl"), encoding="utf-8"))]}
    m = ctranslate2.models.Whisper(MODEL, device="cpu", compute_type="int8", intra_threads=8)
    m.generate(sv(feats_of(audios[0])), [PROMPT], beam_size=5)
    out["sets"] = {}
    for name, clips in sets.items():
        hyps, secs = {"now": [], "guards": [], "fast": []}, {"now": 0.0, "guards": 0.0, "fast": 0.0}
        for i, (cid, _) in enumerate(clips):
            a = sf.read(os.path.join(ROOT, "data", "nchlt_xho", "audio", cid.split("_")[2][:3], cid + ".wav"), dtype="float32")[0]
            f = feats_of(a)
            dur = len(a) / 16000
            cap = int(dur * 8) + 8
            win = max(10, int(np.ceil(dur)) + 1) * 100
            runs = [("now", f, dict(max_length=225)),
                    ("guards", f, dict(max_length=cap, repetition_penalty=1.1, no_repeat_ngram_size=4)),
                    ("fast", f[:, :, :win], dict(max_length=cap, repetition_penalty=1.1, no_repeat_ngram_size=4))]
            for k, x, kw in (runs if i % 2 == 0 else runs[::-1]):
                s = time.perf_counter()
                hyps[k].append(text(m.generate(sv(x), [PROMPT], beam_size=5, **kw)))
                secs[k] += time.perf_counter() - s
            if (i + 1) % 25 == 0:
                print(name, i + 1, flush=True)
        refs = [t for _, t in clips]
        out["sets"][name] = {k: {**{s: round(v, 2) for s, v in score(refs, hyps[k]).items() if s != "n"},
                                 "mean_seconds": round(secs[k] / len(clips), 3),
                                 "same_as_now": sum(normalise(x) == normalise(y) for x, y in zip(hyps[k], hyps["now"]))}
                             for k in hyps}
        out["sets"][name]["clips"] = len(clips)
        print(name, out["sets"][name], flush=True)

json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), mode + ".json"), "w"), indent=1)
print(json.dumps(out))
