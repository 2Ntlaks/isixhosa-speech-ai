"""Score a CTranslate2 (int8) copy of a model on a fixed sample of NCHLT test clips, on this laptop's CPU, and compare
clip by clip with the same model's GPU evaluation (src/baseline.py, fp16). Answers: does the fast engine lose accuracy?

  CT2_USE_MKL=0 .venv/Scripts/python src/eval_ct2.py --model data/models/R-0012-int8 \
      --reference runs/R-0012/eval_nchlt/predictions.jsonl --sample unseen:200 --out runs/R-0013
Same feature extraction, prompt (<|sw|>, transcribe, no timestamps), greedy decoding and token limit (96) as the
NCHLT test evaluation. Writes predictions.jsonl and metrics.json to --out.
"""
import argparse
import json
import os
import random
import sys
import time

import ctranslate2
import numpy as np
import soundfile as sf
from transformers import WhisperProcessor

sys.path.insert(0, os.path.dirname(__file__))
from scoring import NORMALISATION, normalise, score  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--reference", required=True, help="GPU predictions.jsonl of the same model on NCHLT test")
ap.add_argument("--root", default="data")
ap.add_argument("--sample", default="unseen:200", help="seen|unseen|all : number of clips (seeded)")
ap.add_argument("--max-new-tokens", type=int, default=96)
ap.add_argument("--threads", type=int, default=8)
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--out", required=True)
a = ap.parse_args()

ref = [json.loads(l) for l in open(a.reference, encoding="utf-8")]
kind, n = a.sample.split(":")
pool = [r for r in ref if kind == "all" or r.get("text_in_training") == kind]
clips = sorted(random.Random(a.seed).sample(pool, min(int(n), len(pool))), key=lambda r: r["id"])

proc = WhisperProcessor.from_pretrained(a.model)
m = ctranslate2.models.Whisper(a.model, device="cpu", compute_type="int8", intra_threads=a.threads)
prompt = proc.tokenizer.convert_tokens_to_ids(["<|startoftranscript|>", "<|sw|>", "<|transcribe|>", "<|notimestamps|>"])
os.makedirs(a.out, exist_ok=True)
out, t0 = [], time.time()
for i, c in enumerate(clips):
    spk = c["id"].split("_")[2][:3]
    audio, sr = sf.read(os.path.join(a.root, "nchlt_xho", "audio", spk, c["id"] + ".wav"), dtype="float32")
    assert sr == 16000
    feats = proc([audio], sampling_rate=16000, return_tensors="np").input_features
    r = m.generate(ctranslate2.StorageView.from_array(np.ascontiguousarray(feats)), [prompt], beam_size=1,
                   max_length=a.max_new_tokens)
    hyp = proc.tokenizer.decode(r[0].sequences_ids[0], skip_special_tokens=True)
    out.append({"id": c["id"], "text": c["text"], "hyp": hyp, "gpu_hyp": c["hyp"],
                "same_as_gpu": normalise(hyp) == normalise(c["hyp"]), "text_in_training": c.get("text_in_training")})
    if (i + 1) % 25 == 0:
        print(f"  {i + 1}/{len(clips)} clips, {time.time() - t0:.0f} s", flush=True)
secs = time.time() - t0

with open(os.path.join(a.out, "predictions.jsonl"), "w", encoding="utf-8") as f:
    for o in out:
        f.write(json.dumps(o, ensure_ascii=False) + "\n")
fast = score([o["text"] for o in out], [o["hyp"] for o in out])
gpu = score([o["text"] for o in out], [o["gpu_hyp"] for o in out])
metrics = {"model": a.model, "engine": f"ctranslate2 {ctranslate2.__version__} int8 CPU ({a.threads} threads)",
           "reference": a.reference, "sample": a.sample, "seed": a.seed, "clips": len(out),
           "int8_cpu": {"wer": round(fast["wer"], 2), "cer": round(fast["cer"], 2)},
           "gpu_fp16_same_clips": {"wer": round(gpu["wer"], 2), "cer": round(gpu["cer"], 2)},
           "same_output_as_gpu": sum(o["same_as_gpu"] for o in out),
           "seconds_per_clip": round(secs / len(out), 2), "normalisation": NORMALISATION,
           "mkl": os.environ.get("CT2_USE_MKL", "default")}
json.dump(metrics, open(os.path.join(a.out, "metrics.json"), "w"), indent=1)
print(json.dumps(metrics))
