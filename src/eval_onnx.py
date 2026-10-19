"""Score an ONNX (8-bit) copy of a model, the one the in-browser demo uses, on a fixed sample of NCHLT test clips on
this laptop's CPU, and compare clip by clip with the same model's GPU evaluation (src/baseline.py). Like eval_ct2.py.

  .venv-onnx/Scripts/python src/eval_onnx.py --model data/onnx/R-0007 \
      --reference runs/R-0007/eval_nchlt/predictions.jsonl --sample unseen:200 --out runs/R-0017
Loads encoder_model_quantized.onnx + decoder_model_merged_quantized.onnx through optimum's ORTModelForSpeechSeq2Seq.
Same prompt (<|sw|>, transcribe, no timestamps), greedy decoding and token limit (96) as the NCHLT test evaluation.
"""
import argparse
import json
import os
import random
import sys
import time

import soundfile as sf
from optimum.onnxruntime import ORTModelForSpeechSeq2Seq
from transformers import WhisperProcessor

sys.path.insert(0, os.path.dirname(__file__))
from scoring import NORMALISATION, normalise, score  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--reference", required=True, help="GPU predictions.jsonl of the same model on NCHLT test")
ap.add_argument("--root", default="data")
ap.add_argument("--sample", default="unseen:200", help="seen|unseen|all : number of clips (seeded)")
ap.add_argument("--max-new-tokens", type=int, default=96)
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--out", required=True)
a = ap.parse_args()

ref = [json.loads(l) for l in open(a.reference, encoding="utf-8")]
kind, n = a.sample.split(":")
pool = [r for r in ref if kind == "all" or r.get("text_in_training") == kind]
clips = sorted(random.Random(a.seed).sample(pool, min(int(n), len(pool))), key=lambda r: r["id"])

proc = WhisperProcessor.from_pretrained(a.model)
m = ORTModelForSpeechSeq2Seq.from_pretrained(a.model, encoder_file_name="encoder_model_quantized.onnx",
                                             decoder_file_name="decoder_model_merged_quantized.onnx", use_merged=True)
os.makedirs(a.out, exist_ok=True)
out, t0 = [], time.time()
for i, c in enumerate(clips):
    spk = c["id"].split("_")[2][:3]
    audio, sr = sf.read(os.path.join(a.root, "nchlt_xho", "audio", spk, c["id"] + ".wav"), dtype="float32")
    assert sr == 16000
    feats = proc([audio], sampling_rate=16000, return_tensors="pt").input_features
    ids = m.generate(feats, language="sw", task="transcribe", max_new_tokens=a.max_new_tokens)
    hyp = proc.batch_decode(ids, skip_special_tokens=True)[0]
    out.append({"id": c["id"], "text": c["text"], "hyp": hyp, "gpu_hyp": c["hyp"],
                "same_as_gpu": normalise(hyp) == normalise(c["hyp"]), "text_in_training": c.get("text_in_training")})
    if (i + 1) % 25 == 0:
        print(f"  {i + 1}/{len(clips)} clips, {time.time() - t0:.0f} s", flush=True)
secs = time.time() - t0

with open(os.path.join(a.out, "predictions.jsonl"), "w", encoding="utf-8") as f:
    for o in out:
        f.write(json.dumps(o, ensure_ascii=False) + "\n")
onnx = score([o["text"] for o in out], [o["hyp"] for o in out])
gpu = score([o["text"] for o in out], [o["gpu_hyp"] for o in out])
metrics = {"model": a.model, "engine": "onnxruntime int8 (QUInt8 dynamic) CPU via optimum",
           "reference": a.reference, "sample": a.sample, "seed": a.seed, "clips": len(out),
           "onnx_int8": {"wer": round(onnx["wer"], 2), "cer": round(onnx["cer"], 2)},
           "gpu_fp16_same_clips": {"wer": round(gpu["wer"], 2), "cer": round(gpu["cer"], 2)},
           "same_output_as_gpu": sum(o["same_as_gpu"] for o in out),
           "seconds_per_clip": round(secs / len(out), 2), "normalisation": NORMALISATION}
json.dump(metrics, open(os.path.join(a.out, "metrics.json"), "w"), indent=1)
print(json.dumps(metrics))
