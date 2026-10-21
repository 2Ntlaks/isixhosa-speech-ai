"""Swivuriso, isiXhosa part (South Africa African Next Voices, CC BY 4.0, D-0024): prepare clips once, read them back.

  python src/swivuriso.py prepare --source s3://<bucket>/datasets/swivuriso_xho/xho/ --out data/swivuriso_16k

The dataset is published as parquet shards with 48 kHz audio inside (train / dev / dev_test, separate speakers).
`prepare` keeps clips of 1-30 s whose transcript has no [?] (a stretch the transcriber could not make out, so the
text is missing words), writes them as 16 kHz mono 16-bit WAVs, and writes one TSV per split plus summary.json with
what was kept and dropped. Shards from S3 are fetched one per worker and deleted after use, so the disk only ever
holds a few. Text is cleaned with scoring.normalise, the same rules every test is scored with (tags like [um] and
[cs] go, the words stay). Speech recognition only: the licence forbids TTS and voice cloning.
"""
import argparse
import csv
import io
import json
import os
import subprocess
import sys
import tempfile
from math import gcd
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(__file__))
from scoring import normalise  # noqa: E402

csv.field_size_limit(10 ** 8)
FIELDS = ["id", "speaker", "type", "domain", "duration", "file", "text", "raw"]
SPLITS = ("train", "dev", "dev_test")


def load_split(tsv_path, audio_dir):
    """Clips in the same format as nchlt.load_split / fleurs.load_split."""
    with open(tsv_path, encoding="utf-8", newline="") as f:
        return [{"id": "swiv_" + r["id"], "speaker": "swiv_" + r["speaker"], "gender": "", "type": r["type"],
                 "domain": r["domain"], "path": os.path.join(audio_dir, r["file"]), "duration": float(r["duration"]),
                 "text": r["text"]} for r in csv.DictReader(f, delimiter="\t")]


def shard_split(name):
    base = os.path.basename(name)
    return "dev_test" if base.startswith("dev_test-") else base.split("-")[0]


def one_shard(job):
    """Fetch (if on S3) and convert one parquet shard. Returns (split, rows, counts)."""
    import numpy as np
    import pyarrow.parquet as pq
    import soundfile as sf
    from scipy.signal import resample_poly

    src, out, min_s, max_s = job
    split = shard_split(src)
    tmp = None
    if src.startswith("s3://"):
        tmp = tempfile.NamedTemporaryFile(suffix=".parquet", dir=out, delete=False).name
        subprocess.run(["aws", "s3", "cp", src, tmp, "--only-show-errors"], check=True)
    rows, n = [], {"clips": 0, "too_long": 0, "too_short": 0, "unclear": 0, "empty": 0, "unreadable": 0,
                   "decoded_length_outside": 0}
    cols = ["audio", "recorder_uuid", "type", "domain", "file_name", "transcript", "duration"]
    try:
        for batch in pq.ParquetFile(tmp or src).iter_batches(batch_size=32, columns=cols):
            for r in batch.to_pylist():
                n["clips"] += 1
                dur, raw = float(r["duration"] or 0), (r["transcript"] or "").strip()
                if dur > max_s:
                    n["too_long"] += 1
                    continue
                if dur < min_s:
                    n["too_short"] += 1
                    continue
                if "[?" in raw:
                    n["unclear"] += 1
                    continue
                text = normalise(raw)
                if not text:
                    n["empty"] += 1
                    continue
                try:
                    audio, sr = sf.read(io.BytesIO(r["audio"]["bytes"]), dtype="float32")
                except Exception:  # noqa: BLE001 - a broken clip is counted, not fatal
                    n["unreadable"] += 1
                    continue
                if audio.ndim > 1:
                    audio = audio.mean(axis=1)
                if sr != 16000:
                    g = gcd(sr, 16000)
                    audio = resample_poly(audio, 16000 // g, sr // g)
                audio = np.clip(audio, -1, 1)
                if not min_s <= len(audio) / 16000 <= max_s:  # the metadata duration can be wrong
                    n["decoded_length_outside"] += 1
                    continue
                cid = os.path.splitext(r["file_name"])[0].replace(" ", "_")
                rel = f"{split}/{cid}.wav"
                sf.write(os.path.join(out, rel), audio, 16000, subtype="PCM_16")
                rows.append({"id": cid, "speaker": r["recorder_uuid"], "type": r["type"], "domain": r["domain"],
                             "duration": f"{len(audio) / 16000:.3f}", "file": rel, "text": text, "raw": raw})
    finally:
        if tmp:
            os.remove(tmp)
    return split, rows, n


def prepare(a):
    for s in SPLITS:
        os.makedirs(os.path.join(a.out, s), exist_ok=True)
    if a.source.startswith("s3://"):
        ls = subprocess.run(["aws", "s3", "ls", a.source], check=True, capture_output=True, text=True).stdout
        shards = [a.source.rstrip("/") + "/" + line.split()[-1] for line in ls.splitlines() if line.endswith(".parquet")]
    else:
        shards = [os.path.join(a.source, f) for f in os.listdir(a.source) if f.endswith(".parquet")]
    shards.sort()
    print(f"{len(shards)} shards, {a.workers} workers", flush=True)
    rows = {s: [] for s in SPLITS}
    counts = {s: {} for s in SPLITS}
    with Pool(a.workers) as pool:
        for k, (split, r, n) in enumerate(pool.imap_unordered(one_shard, [(s, a.out, a.min_seconds, a.max_seconds)
                                                                          for s in shards]), 1):
            rows[split] += r
            for key, v in n.items():
                counts[split][key] = counts[split].get(key, 0) + v
            print(f"  {k}/{len(shards)} shards, {sum(len(v) for v in rows.values())} clips kept", flush=True)
    summary = {"source": a.source, "min_seconds": a.min_seconds, "max_seconds": a.max_seconds,
               "rule": "keep 1-30 s, drop transcripts containing [?], text = scoring.normalise(transcript)"}
    for s in SPLITS:
        rows[s].sort(key=lambda r: r["id"])
        with open(os.path.join(a.out, f"{s}.tsv"), "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, FIELDS, delimiter="\t")
            w.writeheader()
            w.writerows(rows[s])
        hours = {t: round(sum(float(r["duration"]) for r in rows[s] if r["type"] == t) / 3600, 2)
                 for t in sorted({r["type"] for r in rows[s]})}
        summary[s] = {**counts[s], "kept": len(rows[s]), "kept_hours": round(sum(hours.values()), 2),
                      "kept_hours_by_type": hours, "speakers": len({r["speaker"] for r in rows[s]})}
    with open(os.path.join(a.out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=1), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--source", required=True, help="folder or s3:// prefix holding the xho parquet shards")
    p.add_argument("--out", required=True)
    p.add_argument("--workers", type=int, default=os.cpu_count())
    p.add_argument("--min-seconds", type=float, default=1.0)
    p.add_argument("--max-seconds", type=float, default=30.0)
    prepare(ap.parse_args())
