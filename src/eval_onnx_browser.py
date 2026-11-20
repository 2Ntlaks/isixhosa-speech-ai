"""Score a browser (ONNX) copy of a model the way transformers.js decodes: greedy, plus a loop guard (R-0038).

  C:\\Users\\ntlak\\venvs\\onnx-med\\Scripts\\python src/eval_onnx_browser.py --set fleurs \
      --model C:\\Users\\ntlak\\isixhosa-speech-ai-data\\onnx\\R-0035 --kind q4f16 --out runs/R-0038/A_fleurs

Clips (public sets only, fixed):
  fleurs  the 100 FLEURS test clips of R-0036/R-0037 (seed 1), audio data/fleurs_xh_za/audio/test
  nchlt   200 NCHLT unseen-sentence test clips, drawn as eval_onnx.py draws them (seed 1)
Each clip is compared with R-0035's greedy GPU output (runs/R-0035/legacy_greedy), the fair ceiling for a greedy
browser decoder. Loop guard: if the text's gzip compression ratio is > 2.4, decode again by sampling at temperature
0.2, then 0.4, then 0.6 (seeded), keeping the first that is not repetitive (Whisper's own rule, which the browser
copy would have to re-implement in JavaScript).
"""
import argparse
import json
import os
import random
import sys
import time
import zlib

import onnxruntime as ort
import soundfile as sf
import torch
from optimum.onnxruntime import ORTModelForSpeechSeq2Seq
from transformers import WhisperProcessor

sys.path.insert(0, os.path.dirname(__file__))
from scoring import NORMALISATION, normalise, score  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("--set", required=True, choices=["fleurs", "nchlt"])
ap.add_argument("--model", required=True, help="folder with the .onnx files and the processor/tokenizer files")
ap.add_argument("--kind", default="q4f16", help="file suffix: encoder_model_<kind>.onnx (quantized = R-0027's q8)")
ap.add_argument("--encoder-kind", default=None, help="different encoder suffix, e.g. fp16 (candidate B)")
ap.add_argument("--threads", type=int, default=8)
ap.add_argument("--n", type=int, default=None, help="first n clips only (smoke test)")
ap.add_argument("--out", required=True)
a = ap.parse_args()

legacy = os.path.join(ROOT, "runs", "R-0035", "legacy_greedy", f"eval_{a.set}", "predictions.jsonl")
gpu = {r["id"]: r for r in map(json.loads, open(legacy, encoding="utf-8"))}
if a.set == "fleurs":
    ids = [json.loads(l)["id"] for l in open(os.path.join(ROOT, "runs", "R-0036", "eval_fleurs", "predictions.jsonl"),
                                             encoding="utf-8")]
    clips = [gpu[i] for i in ids]
    path = lambda c: os.path.join(ROOT, "data", "fleurs_xh_za", "audio", "test", c["id"][len("fleurs_"):] + ".wav")
    max_new = 225
else:
    pool = [r for r in gpu.values() if r.get("text_in_training") == "unseen"]
    clips = sorted(random.Random(1).sample(pool, 200), key=lambda r: r["id"])
    path = lambda c: os.path.join(ROOT, "data", "nchlt_xho", "audio", c["id"].split("_")[2][:3], c["id"] + ".wav")
    max_new = 96
clips = clips[: a.n] if a.n else clips

enc = f"encoder_model_{a.encoder_kind or a.kind}.onnx"
dec = f"decoder_model_merged_{a.kind}.onnx"
so = ort.SessionOptions()
so.intra_op_num_threads = a.threads
# ORT 1.27 SimplifiedLayerNormFusion fails on the float16 copies ("InsertedPrecisionFreeCast_... does not exist"), R-0038
so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
proc = WhisperProcessor.from_pretrained(a.model)
m = ORTModelForSpeechSeq2Seq.from_pretrained(a.model, encoder_file_name=enc, decoder_file_name=dec, use_merged=True,
                                             use_io_binding=False, session_options=so)


def ratio(text):
    b = text.encode("utf-8")
    return len(b) / len(zlib.compress(b)) if b else 0.0


def decode(feats, **kw):
    ids = m.generate(feats, language="sw", task="transcribe", max_new_tokens=max_new, **kw)
    return proc.batch_decode(ids, skip_special_tokens=True)[0].strip()


if os.name == "nt":  # keep Windows from sleeping mid-run (R-0038 lost 2 h to sleep); released when the script ends
    import ctypes
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
os.makedirs(a.out, exist_ok=True)
out, t0, audio_s = [], time.time(), 0.0
for i, c in enumerate(clips):
    audio, sr = sf.read(path(c), dtype="float32")
    assert sr == 16000, (c["id"], sr)
    audio_s += len(audio) / sr
    feats = proc([audio], sampling_rate=16000, return_tensors="pt").input_features
    t1 = time.time()
    hyp, tried = decode(feats), [0.0]
    for t in (0.2, 0.4, 0.6):
        if ratio(hyp) <= 2.4:
            break
        torch.manual_seed(1)
        hyp = decode(feats, do_sample=True, temperature=t)
        tried.append(t)
    out.append({"id": c["id"], "text": c["text"], "hyp": hyp, "gpu_greedy_hyp": c["hyp"], "temperatures": tried,
                "runaway": ratio(hyp) > 2.4, "seconds": round(time.time() - t1, 2),
                "same_as_gpu": normalise(hyp) == normalise(c["hyp"]), "text_in_training": c.get("text_in_training")})
    if (i + 1) % 20 == 0:
        print(f"  {i + 1}/{len(clips)} clips, {time.time() - t0:.0f} s", flush=True)
secs = time.time() - t0

with open(os.path.join(a.out, "predictions.jsonl"), "w", encoding="utf-8") as f:
    for o in out:
        f.write(json.dumps(o, ensure_ascii=False) + "\n")
mine = score([o["text"] for o in out], [o["hyp"] for o in out])
ref = score([o["text"] for o in out], [o["gpu_greedy_hyp"] for o in out])
metrics = {"model": a.model, "encoder": enc, "decoder": dec,
           "sizes_mb": {f: round(os.path.getsize(os.path.join(a.model, f)) / 1e6, 2) for f in (enc, dec)},
           "engine": f"onnxruntime {ort.__version__} CPU via optimum, {a.threads} threads, basic graph optimisation, greedy + gzip loop guard",
           "set": a.set, "clips": len(out), "max_new_tokens": max_new,
           "onnx": {"wer": round(mine["wer"], 2), "cer": round(mine["cer"], 2)},
           "r0035_gpu_greedy_same_clips": {"wer": round(ref["wer"], 2), "cer": round(ref["cer"], 2)},
           "same_output_as_gpu": sum(o["same_as_gpu"] for o in out),
           "loop_guard_used": sum(len(o["temperatures"]) > 1 for o in out),
           "runaways_left": sum(o["runaway"] for o in out),
           "seconds": round(secs), "audio_seconds": round(audio_s), "normalisation": NORMALISATION}
json.dump(metrics, open(os.path.join(a.out, "metrics.json"), "w"), indent=1)
print(json.dumps(metrics))
