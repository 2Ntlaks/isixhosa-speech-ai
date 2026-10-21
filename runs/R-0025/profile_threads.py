"""Sequential CPU thread probe. Saves aggregate scores and hashes, never transcripts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
ASSETS = Path(os.environ.get("THETHA_ASSETS_ROOT", ROOT))


def worker(threads):
    os.environ.setdefault("CT2_USE_MKL", "0")
    import ctranslate2
    import numpy as np
    import soundfile as sf
    import torch
    from transformers import WhisperProcessor
    sys.path.insert(0, str(ROOT / "src"))
    from scoring import normalise, score

    torch.set_num_threads(8)  # fixed feature extraction, only CT2 threads change
    rows = [json.loads(s) for s in (ROOT / "runs/R-0021/predictions.jsonl").read_text(encoding="utf-8").splitlines()]
    rows = sorted(random.Random(22).sample(rows, 6), key=lambda r: r["id"])
    model_dir = str(ASSETS / "data/models/R-0019-int8")
    proc = WhisperProcessor.from_pretrained(model_dir, local_files_only=True)
    model = ctranslate2.models.Whisper(model_dir, device="cpu", compute_type="int8", intra_threads=threads)
    prompt = proc.tokenizer.convert_tokens_to_ids(["<|startoftranscript|>", "<|sw|>", "<|transcribe|>", "<|notimestamps|>"])
    items = []
    for row in rows:
        path = ASSETS / "data/nchlt_xho/audio" / row["id"].split("_")[2][:3] / (row["id"] + ".wav")
        audio, sr = sf.read(path, dtype="float32")
        assert sr == 16000
        start = time.perf_counter()
        feats = proc([audio], sampling_rate=sr, return_tensors="pt").input_features
        items.append((row, feats, time.perf_counter() - start, len(audio) / sr))

    def generate(feats):
        result = model.generate(ctranslate2.StorageView.from_array(np.ascontiguousarray(feats.numpy())),
                                [prompt], beam_size=5, max_length=225)
        return proc.tokenizer.decode(result[0].sequences_ids[0], skip_special_tokens=True)

    generate(items[0][1])  # same warm-up for every setting
    hyps, records = [], []
    for row, feats, feature_s, audio_s in items:
        start = time.perf_counter()
        hyp = generate(feats)
        elapsed = time.perf_counter() - start
        hyps.append(hyp)
        records.append({"id": row["id"], "audio_seconds": audio_s, "feature_seconds": feature_s,
                        "generate_seconds": elapsed,
                        "output_sha256": hashlib.sha256(normalise(hyp).encode()).hexdigest()})
        print(f"threads={threads} clip={len(records)}/6 seconds={elapsed:.3f}", flush=True)
    result = {"threads": threads, "beam_size": 5, "max_length": 225, "seed": 22,
              "scores": score([r["text"] for r in rows], hyps), "clips": records,
              "mean_generate_seconds": sum(r["generate_seconds"] for r in records) / len(records)}
    (Path(__file__).parent / f"threads-{threads}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "clips"}), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", type=int)
    args = ap.parse_args()
    if args.worker:
        worker(args.worker)
    else:
        for threads in (4, 8, 2, 1):
            subprocess.run([sys.executable, "-B", __file__, "--worker", str(threads)], cwd=ROOT, check=True)
