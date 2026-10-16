"""Stage 1: score a stock (untrained-on-isiXhosa) Whisper model on the NCHLT test set.

  python src/baseline.py --xml data/nchlt_xho/transcriptions/nchlt_xho.tst.xml --root data --out out \
      --model openai/whisper-small --language auto

--language auto lets Whisper pick a language per clip (it has no isiXhosa tag) and records which one it picked.
--dry-run skips the model and uses the reference text as the "guess" (should score 0 %), to test the plumbing.
Writes to --out: predictions.jsonl, metrics.json, samples.md.
"""
import argparse
import collections
import json
import os
import platform
import random
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from nchlt import load_split  # noqa: E402
from scoring import NORMALISATION, normalise, score  # noqa: E402


def whisper_transcriber(model_name, language, batch_size):
    import numpy as np
    import soundfile as sf
    import torch
    import torchaudio
    from transformers import WhisperForConditionalGeneration, WhisperProcessor

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    proc = WhisperProcessor.from_pretrained(model_name)
    model = WhisperForConditionalGeneration.from_pretrained(model_name, torch_dtype=dtype).to(device).eval()

    def load(path):
        audio, sr = sf.read(path, dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if sr != 16000:
            audio = torchaudio.functional.resample(torch.from_numpy(audio), sr, 16000).numpy()
        return np.ascontiguousarray(audio)

    def transcribe(clips):
        feats = proc([load(c["path"]) for c in clips], sampling_rate=16000, return_tensors="pt").input_features
        feats = feats.to(device, dtype)
        with torch.no_grad():
            if language == "auto":
                ids = model.detect_language(input_features=feats)
                langs = [t.strip("<|>") for t in proc.tokenizer.convert_ids_to_tokens(ids.tolist())]
            else:
                langs = [language] * len(clips)
            out = model.generate(feats, language=langs, task="transcribe", max_new_tokens=96)
        return proc.batch_decode(out, skip_special_tokens=True), langs

    env = {"torch": torch.__version__, "device": device,
           "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None}
    return transcribe, env


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="openai/whisper-small")
    ap.add_argument("--language", default="auto")
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--limit", type=int, default=0, help="only the first N clips (0 = all)")
    ap.add_argument("--samples", type=int, default=20)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    clips = load_split(a.xml, a.root)
    if a.limit:
        clips = clips[: a.limit]
    print(f"{len(clips)} clips, {sum(c['duration'] for c in clips) / 3600:.2f} h, "
          f"{len({c['speaker'] for c in clips})} speakers", flush=True)

    if a.dry_run:
        transcribe, env = (lambda b: ([c["text"] for c in b], ["dry"] * len(b))), {"device": "none"}
    else:
        transcribe, env = whisper_transcriber(a.model, a.language, a.batch_size)

    order = sorted(range(len(clips)), key=lambda i: clips[i]["duration"])  # similar lengths batch well
    t0 = time.time()
    for k in range(0, len(order), a.batch_size):
        batch = [clips[i] for i in order[k: k + a.batch_size]]
        hyps, langs = transcribe(batch)
        for c, h, l in zip(batch, hyps, langs):
            c["hyp"], c["lang"] = h.strip(), l
        if (k // a.batch_size) % 10 == 0:
            print(f"  {k + len(batch)}/{len(clips)} clips, {time.time() - t0:.0f} s", flush=True)
    secs = time.time() - t0

    for c in clips:
        s = score([c["text"]], [c["hyp"]])
        c["wer"], c["cer"] = round(s["wer"], 1), round(s["cer"], 1)
        c["exact"] = normalise(c["text"]) == normalise(c["hyp"])
    with open(os.path.join(a.out, "predictions.jsonl"), "w", encoding="utf-8") as f:
        for c in clips:
            f.write(json.dumps({k: v for k, v in c.items() if k != "path"}, ensure_ascii=False) + "\n")

    def group(key):
        out = {}
        for g in sorted({c[key] for c in clips}):
            sub = [c for c in clips if c[key] == g]
            s = score([c["text"] for c in sub], [c["hyp"] for c in sub])
            out[g] = {"wer": round(s["wer"], 1), "cer": round(s["cer"], 1), "n": s["n"]}
        return out

    total = score([c["text"] for c in clips], [c["hyp"] for c in clips])
    if not a.dry_run:
        import transformers
        env["transformers"] = transformers.__version__
    metrics = {
        "model": a.model, "language": a.language, "test_set": os.path.basename(a.xml),
        "clips": len(clips), "audio_hours": round(sum(c["duration"] for c in clips) / 3600, 3),
        "wer": round(total["wer"], 2), "cer": round(total["cer"], 2),
        "exact_match_pct": round(100 * sum(c["exact"] for c in clips) / len(clips), 2),
        "empty_output_pct": round(100 * sum(not normalise(c["hyp"]) for c in clips) / len(clips), 2),
        "detected_languages": dict(collections.Counter(c["lang"] for c in clips).most_common()),
        "per_speaker": group("speaker"), "per_gender": group("gender"),
        "normalisation": NORMALISATION, "seconds": round(secs, 1), "batch_size": a.batch_size,
        "env": {**env, "python": platform.python_version()},
    }
    with open(os.path.join(a.out, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    # samples: a fixed, seeded pick spread over the speakers, so the founder can listen and judge
    rng = random.Random(a.seed)
    by_spk = collections.defaultdict(list)
    for c in clips:
        by_spk[c["speaker"]].append(c)
    picks = []
    while len(picks) < min(a.samples, len(clips)):
        for spk in sorted(by_spk):
            pool = [c for c in by_spk[spk] if c not in picks]
            if pool and len(picks) < a.samples:
                picks.append(rng.choice(pool))
    with open(os.path.join(a.out, "samples.md"), "w", encoding="utf-8") as f:
        f.write(f"# Samples: {a.model}, language={a.language}\n\n")
        f.write("| clip | speaker | Whisper's language | reference (NCHLT) | Whisper's output | WER % | CER % |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for c in picks:
            f.write(f"| {c['id']} | {c['speaker']} {c['gender'][0]} | {c['lang']} | {c['text']} | "
                    f"{c['hyp'].replace('|', '/')} | {c['wer']} | {c['cer']} |\n")
    print(json.dumps({k: metrics[k] for k in ("wer", "cer", "exact_match_pct", "detected_languages", "seconds")}))


if __name__ == "__main__":
    main()
