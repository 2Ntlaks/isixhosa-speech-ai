"""Compare live inference with its pre-change implementation. No transcripts are written."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import threading
import time
import types

ROOT = Path(__file__).resolve().parents[2]
ASSETS = Path(os.environ.get("THETHA_ASSETS_ROOT", ROOT))
BASELINE = "20b9468"  # same live.py as local 2dff2ea; retained as a PR ancestor for reproduction
os.environ.setdefault("CT2_USE_MKL", "0")
sys.path.insert(0, str(ROOT / "src"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--long", choices=["baseline", "candidate"])
    args = ap.parse_args()
    import numpy as np
    import psutil
    import soundfile as sf
    import torch
    import live
    from scoring import normalise, score

    torch.set_num_threads(8)
    baseline = types.ModuleType("baseline_live")
    baseline.__file__ = str(ROOT / "src/live.py")
    code = subprocess.check_output(["git", "show", f"{BASELINE}:src/live.py"], cwd=ROOT, text=True, encoding="utf-8")
    exec(compile(code, "baseline_live.py", "exec"), baseline.__dict__)
    baseline.dtype = torch.bfloat16
    baseline.MODELS = live.MODELS = str(ASSETS / "data/models")
    name = "R-0019-int8"
    rows = [json.loads(s) for s in (ROOT / "runs/R-0021/predictions.jsonl").read_text(encoding="utf-8").splitlines()]
    rows = sorted(random.Random(22).sample(rows, 32), key=lambda r: r["id"])
    audios = []
    for row in rows:
        path = ASSETS / "data/nchlt_xho/audio" / row["id"].split("_")[2][:3] / (row["id"] + ".wav")
        audio, sr = sf.read(path, dtype="float32")
        assert sr == 16000
        audios.append(audio)

    # A single shared engine makes alternating single-clip timings independent of load order.
    live.transcribe(np.zeros(16000, dtype=np.float32), name)
    baseline.loaded = live.loaded
    engines = {"baseline": baseline, "candidate": live}
    process = psutil.Process()

    def digest(text):
        return hashlib.sha256(normalise(text).encode()).hexdigest()

    def timed(module, audio):
        peak = [process.memory_info().rss]
        stop = threading.Event()

        def monitor():
            while not stop.wait(0.02):
                peak[0] = max(peak[0], process.memory_info().rss)

        thread = threading.Thread(target=monitor)
        thread.start()
        try:
            started = time.perf_counter()
            text, model_seconds = module.transcribe(audio, name)
            wall = time.perf_counter() - started
            peak[0] = max(peak[0], process.memory_info().rss)
        finally:
            stop.set()
            thread.join()
        return text, {"wall_seconds": wall, "model_seconds": model_seconds,
                      "peak_working_set_bytes": peak[0], "output_sha256": digest(text)}

    config = {"baseline_commit": BASELINE,
              "candidate_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "candidate_source_sha256": hashlib.sha256((ROOT / "src/live.py").read_bytes()).hexdigest(),
              "model": name, "threads": 8, "beam_size": 5,
              "max_length": 225, "seed": 22, "chunk_batch_size": 1}
    if args.long:
        parts, refs, duration = [], [], 0
        for row, audio in zip(rows, audios):
            parts.append(audio)
            refs.append(row["text"])
            duration += len(audio) / 16000
            if duration >= 45:
                break
        audio = np.concatenate(parts)
        text, timing = timed(engines[args.long], audio)
        result = {"config": config, "variant": args.long, "audio_seconds": duration,
                  "source_ids": [row["id"] for row in rows[:len(parts)]],
                  "scores": score([" ".join(refs)], [text]), **timing}
        path = Path(__file__).parent / f"long-{args.long}.json"
        path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result), flush=True)
        return

    records, predictions = [], {k: [] for k in engines}
    for index, (row, audio) in enumerate(zip(rows, audios)):
        record = {"id": row["id"], "audio_seconds": len(audio) / 16000}
        order = list(engines) if index % 2 == 0 else list(reversed(engines))
        for key in order:
            text, record[key] = timed(engines[key], audio)
            predictions[key].append(text)
        records.append(record)
        print(f"paired clip {index + 1}/32, identical={record['baseline']['output_sha256'] == record['candidate']['output_sha256']}", flush=True)
        # Preserve partial evidence if the benchmark is interrupted.
        (Path(__file__).parent / "validation-progress.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    result = {"config": config, "clips": records,
              "scores": {key: score([r["text"] for r in rows], predictions[key]) for key in engines},
              "identical_outputs": sum(r["baseline"]["output_sha256"] == r["candidate"]["output_sha256"] for r in records),
              "mean_wall_seconds": {key: sum(r[key]["wall_seconds"] for r in records) / len(records) for key in engines}}
    (Path(__file__).parent / "validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "clips"}), flush=True)


if __name__ == "__main__":
    main()
