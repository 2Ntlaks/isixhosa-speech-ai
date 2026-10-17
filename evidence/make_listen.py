"""Build a local listening page: the 20 fixed NCHLT test clips from R-0001, each with its audio, the true text and what
four models wrote (plain Whisper, Swahili tag, whisper-small trained, whisper-medium trained), wrong words marked.

  python evidence/make_listen.py            (needs jiwer, like src/scoring.py)
Writes data/listen/listen-R-0012.html. The page embeds NCHLT audio, so it stays in data/ (gitignored): never commit or
upload it (NCHLT licence: no re-hosting of the raw audio).
"""
import base64
import difflib
import html
import json
import os
import struct
import sys
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from scoring import normalise, score  # noqa: E402

CLIPS = os.path.join(ROOT, "data", "listen", "R-0001")
OUT = os.path.join(ROOT, "data", "listen", "listen-R-0012.html")
MODELS = [  # (run, label, what it is, predictions file)
    ("R-0001", "Plain Whisper", "no training, guesses the language", "runs/R-0001/predictions.jsonl"),
    ("R-0003", "+ Swahili tag", "no training", "runs/R-0003/predictions.jsonl"),
    ("R-0007", "whisper-small", "trained, NCHLT + FLEURS", "runs/R-0007/eval_nchlt/predictions.jsonl"),
    ("R-0012", "whisper-medium", "trained, NCHLT + FLEURS · best", "runs/R-0012/eval_nchlt/predictions.jsonl"),
]
BARS = 72


def load(path):
    return {d["id"]: d for d in map(json.loads, open(os.path.join(ROOT, path), encoding="utf-8"))}


def peaks(path):
    """Loudness envelope for the waveform drawing: BARS values in 0..1."""
    with wave.open(path) as w:
        n, width = w.getnframes(), w.getsampwidth()
        assert width == 2 and w.getnchannels() == 1, path
        x = struct.unpack(f"<{n}h", w.readframes(n))
    step = max(1, n // BARS)
    vals = [max(abs(v) for v in x[i:i + step]) for i in range(0, step * BARS, step)]
    top = max(vals) or 1
    return [round(v / top, 3) for v in vals]


def marked(ref, hyp):
    """Hypothesis words as HTML, words that don't line up with the reference marked."""
    r, h = normalise(ref).split(), normalise(hyp).split()
    out = []
    for op, _, _, j1, j2 in difflib.SequenceMatcher(a=r, b=h, autojunk=False).get_opcodes():
        for w in h[j1:j2]:
            out.append(html.escape(w) if op == "equal" else f"<mark>{html.escape(w)}</mark>")
    if not h:
        return '<span class="empty">(wrote nothing)</span>'
    return " ".join(out)


preds = {run: load(path) for run, _, _, path in MODELS}
clips = []
for f in sorted(os.listdir(CLIPS)):
    if not f.endswith(".wav"):
        continue
    cid = f[:-4]
    ref = preds["R-0012"][cid]["text"]
    rows = []
    for run, label, what, _ in MODELS:
        p = preds[run][cid]
        cer = score([ref], [p["hyp"]])["cer"]
        rows.append({"run": run, "label": label, "what": what, "cer": round(cer, 1), "exact": normalise(ref) == normalise(p["hyp"]),
                     "html": marked(ref, p["hyp"])})
    audio = base64.b64encode(open(os.path.join(CLIPS, f), "rb").read()).decode()
    clips.append({"id": cid, "speaker": cid.split("_")[2][:3], "gender": "woman" if cid.split("_")[2][3] == "f" else "man",
                  "seconds": preds["R-0012"][cid]["duration"], "ref": html.escape(normalise(ref)),
                  "seen": preds["R-0012"][cid].get("text_in_training", "seen"), "rows": rows, "peaks": peaks(os.path.join(CLIPS, f)),
                  "audio": audio})

exact = {run: sum(c["rows"][i]["exact"] for c in clips) for i, (run, *_) in enumerate(MODELS)}
corpus = {run: round(score([preds["R-0012"][c["id"]]["text"] for c in clips], [preds[run][c["id"]]["hyp"] for c in clips])["cer"], 1)
          for run, *_ in MODELS}
tpl = open(os.path.join(ROOT, "evidence", "listen.template.html"), encoding="utf-8").read()
data = {"clips": clips, "models": [{"run": r, "label": l, "what": w, "exact": exact[r], "cer": corpus[r]} for r, l, w, _ in MODELS]}
page = tpl.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
open(OUT, "w", encoding="utf-8").write(page)
print(f"wrote {OUT} ({len(page) // 1024} KB, {len(clips)} clips); exact per model {exact}; CER on these 20 {corpus}")
