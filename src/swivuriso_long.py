"""Swivuriso long clips (over 30 s, unused until now) -> training pieces of at most 28 s, cut at pauses between words.

  python src/swivuriso_long.py extract --source s3://<bucket>/datasets/swivuriso_xho/xho/ --out data/swiv_long \
      --exclude-texts data/test_texts.txt                     # CPU: long train clips -> 16 kHz WAVs + long.tsv
  python src/swivuriso_long.py cut --out data/swiv_long        # GPU: word timings + cutting -> pieces.tsv

Whisper hears at most 30 s, so a 2-minute recording cannot be trained on whole. A forced aligner (torchaudio's MMS_FA,
a multilingual wav2vec2 model that knows the Latin alphabet) finds when each word of the transcript is spoken. Pieces
then end in the widest pause before 28 s, so no word is cut in half. Every piece keeps its words' alignment scores
(how sure the aligner is), so poor alignments can be filtered after a quality check.
Rules kept from src/swivuriso.py: train split only (dev and test speakers never touched), clips with [?] dropped
(missing words), text = scoring.normalise(transcript). New: a clip whose text contains any test or dev sentence of
3+ words is dropped whole. Speech recognition only: the licence forbids TTS and voice cloning.
"""
import argparse
import csv
import io
import json
import os
import subprocess
import sys
import tempfile
import unicodedata
from math import gcd
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(__file__))
from scoring import normalise  # noqa: E402

csv.field_size_limit(10 ** 8)
LONG_FIELDS = ["id", "speaker", "type", "domain", "duration", "file", "text"]
PIECE_FIELDS = ["id", "speaker", "type", "domain", "duration", "file", "text", "source", "start", "end",
                "score_min", "score_mean", "gap_before", "gap_after"]
SR = 16000


def aligner_text(text):
    """Words as the aligner spells them (a-z and '), or None if a word has other characters (digits etc.)."""
    words = []
    for w in text.split():
        w = "".join(c for c in unicodedata.normalize("NFKD", w) if not unicodedata.combining(c))
        if not w or any(c not in "abcdefghijklmnopqrstuvwxyz'" for c in w):
            return None
        words.append(w)
    return words


def leaks(text, excluded):
    """True if the clip's text contains a test/dev sentence of 3+ words."""
    padded = f" {text} "
    return any(f" {s} " in padded for s in excluded)


def one_shard(job):
    import numpy as np
    import pyarrow.parquet as pq
    import soundfile as sf
    from scipy.signal import resample_poly

    src, out, min_s, excluded_path = job
    excluded = [s for s in open(excluded_path, encoding="utf-8").read().splitlines() if len(s.split()) >= 3]
    base = os.path.basename(src)
    n = {"clips": 0, "short": 0, "unclear": 0, "empty": 0, "spelling": 0, "leak": 0, "unreadable": 0}
    rows, tmp = [], None
    if not base.startswith("train-"):
        return rows, n
    if src.startswith("s3://"):
        tmp = tempfile.NamedTemporaryFile(suffix=".parquet", dir=out, delete=False).name
        subprocess.run(["aws", "s3", "cp", src, tmp, "--only-show-errors"], check=True)
    cols = ["audio", "recorder_uuid", "type", "domain", "file_name", "transcript", "duration"]
    try:
        for batch in pq.ParquetFile(tmp or src).iter_batches(batch_size=16, columns=cols):
            for r in batch.to_pylist():
                n["clips"] += 1
                raw = (r["transcript"] or "").strip()
                if float(r["duration"] or 0) <= min_s:
                    n["short"] += 1
                    continue
                if "[?" in raw:
                    n["unclear"] += 1
                    continue
                text = normalise(raw)
                if not text:
                    n["empty"] += 1
                    continue
                if aligner_text(text) is None:
                    n["spelling"] += 1
                    continue
                if leaks(text, excluded):
                    n["leak"] += 1
                    continue
                try:
                    audio, sr = sf.read(io.BytesIO(r["audio"]["bytes"]), dtype="float32")
                except Exception:  # noqa: BLE001 - counted, not fatal
                    n["unreadable"] += 1
                    continue
                if audio.ndim > 1:
                    audio = audio.mean(axis=1)
                if sr != SR:
                    g = gcd(sr, SR)
                    audio = resample_poly(audio, SR // g, sr // g)
                audio = np.clip(audio, -1, 1)
                if len(audio) / SR <= min_s:  # the metadata duration can be wrong
                    n["short"] += 1
                    continue
                cid = os.path.splitext(r["file_name"])[0].replace(" ", "_")
                rel = f"long/{cid}.wav"
                sf.write(os.path.join(out, rel), audio, SR, subtype="PCM_16")
                rows.append({"id": cid, "speaker": r["recorder_uuid"], "type": r["type"], "domain": r["domain"],
                             "duration": f"{len(audio) / SR:.3f}", "file": rel, "text": text})
    finally:
        if tmp:
            os.remove(tmp)
    return rows, n


def extract(a):
    os.makedirs(os.path.join(a.out, "long"), exist_ok=True)
    if a.source.startswith("s3://"):
        ls = subprocess.run(["aws", "s3", "ls", a.source], check=True, capture_output=True, text=True).stdout
        shards = [a.source.rstrip("/") + "/" + line.split()[-1] for line in ls.splitlines() if line.endswith(".parquet")]
    else:
        shards = [os.path.join(a.source, f) for f in os.listdir(a.source) if f.endswith(".parquet")]
    shards = sorted(s for s in shards if os.path.basename(s).startswith("train-"))
    print(f"{len(shards)} train shards, {a.workers} workers", flush=True)
    rows, counts = [], {}
    with Pool(a.workers) as pool:
        for k, (r, n) in enumerate(pool.imap_unordered(one_shard, [(s, a.out, a.min_seconds, a.exclude_texts) for s in shards]), 1):
            rows += r
            for key, v in n.items():
                counts[key] = counts.get(key, 0) + v
            print(f"  {k}/{len(shards)} shards, {len(rows)} long clips kept", flush=True)
    rows.sort(key=lambda r: r["id"])
    with open(os.path.join(a.out, "long.tsv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, LONG_FIELDS, delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    summary = {"rule": f"train split, longer than {a.min_seconds} s, no [?], a-z spelling, no test/dev sentence of 3+ words",
               **counts, "long_clips_kept": len(rows), "long_hours_kept": round(sum(float(r["duration"]) for r in rows) / 3600, 2),
               "speakers": len({r["speaker"] for r in rows})}
    json.dump(summary, open(os.path.join(a.out, "extract_summary.json"), "w"), indent=2)
    print(json.dumps(summary, indent=1), flush=True)


def word_timings(model, tokenizer, aligner, audio, words, device, chunk_s=30):
    """-> [(start s, end s, score 0-1)] per word. Emissions are computed in 30 s windows to bound memory."""
    import torch
    wav = torch.from_numpy(audio).unsqueeze(0)
    parts = []
    with torch.inference_mode():
        for i in range(0, wav.size(1), chunk_s * SR):
            piece = wav[:, i:i + chunk_s * SR]
            if piece.size(1) < 400:  # shorter than one wav2vec2 frame window
                break
            parts.append(model(piece.to(device))[0].cpu())
    emission = torch.cat(parts, dim=1)
    spans = aligner(emission[0], tokenizer(words))
    ratio = wav.size(1) / emission.size(1) / SR  # seconds per emission frame (~0.02)
    out = []
    for s in spans:
        frames = sum(t.end - t.start for t in s)
        out.append((s[0].start * ratio, s[-1].end * ratio, sum(t.score * (t.end - t.start) for t in s) / frames))
    return out


def pieces(timings, duration, max_s=28.0, min_s=8.0, pad=0.3):
    """Group words into pieces of at most max_s, each ending at the widest pause after min_s. -> [(first, last)]."""
    out, i, n = [], 0, len(timings)
    while i < n:
        start = timings[i][0]
        j = i
        while j + 1 < n and timings[j + 1][1] - start <= max_s - 2 * pad:
            j += 1
        if j + 1 == n:
            k = j
        else:
            options = [m for m in range(i, j + 1) if timings[m][1] - start >= min_s] or [j]
            k = max(options, key=lambda m: timings[m + 1][0] - timings[m][1])
        out.append((i, k))
        i = k + 1
    return out


def cut(a):
    import numpy as np
    import soundfile as sf
    import torch
    import torchaudio

    device = "cuda" if torch.cuda.is_available() else "cpu"
    bundle = torchaudio.pipelines.MMS_FA
    model = bundle.get_model(with_star=False).to(device).eval()
    tokenizer, aligner = bundle.get_tokenizer(), bundle.get_aligner()
    with open(os.path.join(a.out, "long.tsv"), encoding="utf-8", newline="") as f:
        clips = list(csv.DictReader(f, delimiter="\t"))
    if a.limit:
        clips = clips[:a.limit]
    os.makedirs(os.path.join(a.out, "pieces"), exist_ok=True)
    rows, n = [], {"clips": len(clips), "failed": 0}
    for c_i, c in enumerate(clips, 1):
        audio, sr = sf.read(os.path.join(a.out, c["file"]), dtype="float32")
        words = c["text"].split()
        try:
            t = word_timings(model, tokenizer, aligner, audio, aligner_text(c["text"]), device)
        except Exception as e:  # noqa: BLE001 - e.g. transcript longer than the audio allows; counted
            n["failed"] += 1
            print(f"  align failed {c['id']}: {e!r}"[:200], flush=True)
            continue
        dur = len(audio) / SR
        for p_i, (i, k) in enumerate(pieces(t, dur, a.max_seconds)):
            before = t[i][0] - (t[i - 1][1] if i > 0 else 0.0)
            after = (t[k + 1][0] if k + 1 < len(t) else dur) - t[k][1]
            s = max(0.0, t[i][0] - min(a.pad, before / 2))
            e = min(dur, t[k][1] + min(a.pad, after / 2))
            pid = f"{c['id']}_{p_i:03d}"
            rel = f"pieces/{pid}.wav"
            sf.write(os.path.join(a.out, rel), audio[int(s * SR):int(e * SR)], SR, subtype="PCM_16")
            scores = [x[2] for x in t[i:k + 1]]
            rows.append({"id": pid, "speaker": c["speaker"], "type": c["type"], "domain": c["domain"],
                         "duration": f"{e - s:.3f}", "file": rel, "text": " ".join(words[i:k + 1]), "source": c["id"],
                         "start": f"{s:.2f}", "end": f"{e:.2f}", "score_min": f"{min(scores):.3f}",
                         "score_mean": f"{float(np.mean(scores)):.3f}", "gap_before": f"{before:.2f}", "gap_after": f"{after:.2f}"})
        if a.delete_long:
            os.remove(os.path.join(a.out, c["file"]))
        if c_i % 200 == 0:
            print(f"  {c_i}/{len(clips)} clips, {len(rows)} pieces", flush=True)
    with open(os.path.join(a.out, "pieces.tsv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, PIECE_FIELDS, delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    durs = [float(r["duration"]) for r in rows]
    summary = {**n, "pieces": len(rows), "hours": round(sum(durs) / 3600, 2), "max_seconds": round(max(durs, default=0), 2),
               "median_seconds": round(float(np.median(durs)) if durs else 0, 2), "device": device}
    json.dump(summary, open(os.path.join(a.out, "cut_summary.json"), "w"), indent=2)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("extract")
    p.add_argument("--source", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--exclude-texts", required=True, help="one normalised test/dev sentence per line")
    p.add_argument("--workers", type=int, default=os.cpu_count())
    p.add_argument("--min-seconds", type=float, default=30.0, help="only clips longer than this (shorter ones are already used)")
    p = sub.add_parser("cut")
    p.add_argument("--out", required=True)
    p.add_argument("--max-seconds", type=float, default=28.0)
    p.add_argument("--pad", type=float, default=0.3, help="silence kept around a piece, at most half the pause")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--delete-long", action="store_true", help="remove each long WAV once cut (saves disk)")
    a = ap.parse_args()
    extract(a) if a.cmd == "extract" else cut(a)
