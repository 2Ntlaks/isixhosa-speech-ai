"""VAD on vs off for the live page path (src/live.py), R-0027 int8, laptop CPU. Rule set before running:
VAD stays default if its CER is at most 0.3 worse than fixed 30 s cuts on BOTH the short clips and the long recordings."""
import json, os, random, sys, time
import numpy as np
SC = sys.argv[1]
sys.path.insert(0, "src")
import live, fleurs, testsets
from scoring import score, normalise
live.MODELS = os.path.join(SC, "models", "whisper-small-isixhosa@f06d9358")
live.CPU_THREADS = 8
pool = [c for c in fleurs.load_split(os.path.join(SC, "fleurs_tsv", "test.tsv"), os.path.join(SC, "fleurs_dl", "audio", "test")) if c["duration"] <= 30]
used = {c["id"] for c in random.Random(7).sample(pool, 40)}          # the first check's clips
rest = [c for c in pool if c["id"] not in used]
rng = random.Random(2026)
short = rng.sample(rest, 120)
left = [c for c in rest if c not in short]
longs = []
for k in range(15):
    parts = rng.sample(left, rng.choice([3, 4]))
    gaps = [rng.uniform(1.0, 3.0) for _ in parts[1:]]
    audio = [testsets.read16k(parts[0]["path"])]
    for p, g in zip(parts[1:], gaps):
        audio += [np.zeros(int(g * 16000), dtype=np.float32), testsets.read16k(p["path"])]
    a = np.concatenate(audio)
    if len(a) > 30 * 16000:
        longs.append((" ".join(p["text"] for p in parts), a))
print(f"{len(short)} short clips, {len(longs)} long recordings ({min(len(a) for _, a in longs)/16000:.0f}-{max(len(a) for _, a in longs)/16000:.0f} s)", flush=True)
res = {}
for vad in (False, True):
    live.VAD = vad
    t = time.time()
    hs = [live.transcribe(testsets.read16k(c["path"]), "ct2-int8")[0] for c in short]
    hl = [live.transcribe(a, "ct2-int8")[0] for _, a in longs]
    s1, s2 = score([c["text"] for c in short], hs), score([r for r, _ in longs], hl)
    res[vad] = {"short": s1, "long": s2, "hyps_short": hs, "hyps_long": hl, "seconds": round(time.time() - t)}
    print(f"VAD {vad}: short WER {s1['wer']:.2f} CER {s1['cer']:.2f} | long WER {s2['wer']:.2f} CER {s2['cer']:.2f} | {res[vad]['seconds']} s", flush=True)
d_short = res[True]["short"]["cer"] - res[False]["short"]["cer"]
d_long = res[True]["long"]["cer"] - res[False]["long"]["cer"]
better = [sum(score([r], [h])["cer"] < score([r], [o])["cer"] for r, h, o in zip(refs, res[True][k], res[False][k])) for k, refs in (("hyps_short", [c["text"] for c in short]), ("hyps_long", [r for r, _ in longs]))]
worse = [sum(score([r], [h])["cer"] > score([r], [o])["cer"] for r, h, o in zip(refs, res[True][k], res[False][k])) for k, refs in (("hyps_short", [c["text"] for c in short]), ("hyps_long", [r for r, _ in longs]))]
verdict = "PASS: keep VAD on" if d_short <= 0.3 and d_long <= 0.3 else "FAIL: VAD off by default"
print(f"CER change with VAD: short {d_short:+.2f} (better {better[0]}, worse {worse[0]}), long {d_long:+.2f} (better {better[1]}, worse {worse[1]}) -> {verdict}")
json.dump({str(k): {kk: vv for kk, vv in v.items() if not kk.startswith("hyps")} for k, v in res.items()} | {"verdict": verdict, "better": better, "worse": worse}, open(os.path.join(SC, "vad_check.json"), "w"), indent=1)
