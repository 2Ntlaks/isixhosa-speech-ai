"""Check src/swivuriso_long.py on the laptop with known answers: NCHLT test clips of one speaker are joined into
~60 s "long clips"; the true time span of every word's clip is known. Then: (1) does each aligned word fall inside its
own clip? (2) do cuts land between clips' words cleanly? (3) R-0019-int8 on the pieces vs the piece text (the same
quality check the cloud job uses). Writes runs/R-0027/check_cutter.json (counts and scores only).

  CT2_USE_MKL=0 .venv/Scripts/python runs/R-0027/check_cutter.py
"""
import csv, json, os, random, subprocess, sys
import numpy as np, soundfile as sf
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))
import nchlt
from scoring import normalise, score
from swivuriso_long import aligner_text, LONG_FIELDS

OUT = os.path.join(os.environ.get("TMP", "/tmp"), "swiv_long_check")
os.makedirs(os.path.join(OUT, "long"), exist_ok=True)
clips = [c for c in nchlt.load_split(os.path.join(ROOT, "data/nchlt_xho/transcriptions/nchlt_xho.tst.xml"), os.path.join(ROOT, "data"))
         if normalise(c["text"]) and aligner_text(normalise(c["text"]))]
rng = random.Random(7)
truth, rows = {}, []
for spk in sorted({c["speaker"] for c in clips}):
    mine = rng.sample([c for c in clips if c["speaker"] == spk], 14)
    audio, spans, t = [], [], 0.0
    for c in mine:
        x = sf.read(c["path"], dtype="float32")[0]
        words = normalise(c["text"]).split()
        spans += [(t, t + len(x) / 16000)] * len(words)
        audio.append(x); t += len(x) / 16000
    lid = f"nchltlong_{spk}"
    sf.write(os.path.join(OUT, "long", lid + ".wav"), np.concatenate(audio), 16000, subtype="PCM_16")
    text = " ".join(normalise(c["text"]) for c in mine)
    rows.append({"id": lid, "speaker": spk, "type": "scripted", "domain": "nchlt", "duration": f"{t:.3f}", "file": f"long/{lid}.wav", "text": text})
    truth[lid] = spans
with open(os.path.join(OUT, "long.tsv"), "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, LONG_FIELDS, delimiter="\t"); w.writeheader(); w.writerows(rows)
print(len(rows), "long clips,", round(sum(float(r["duration"]) for r in rows) / 60, 1), "min", flush=True)
subprocess.run([sys.executable, os.path.join(ROOT, "src/swivuriso_long.py"), "cut", "--out", OUT], check=True)

pieces = list(csv.DictReader(open(os.path.join(OUT, "pieces.tsv"), encoding="utf-8"), delimiter="\t"))
# (1)+(2): every word of a piece must come from clips whose time spans overlap the piece's cut window
inside = total = 0
for p in pieces:
    words = p["text"].split()
    src = truth[p["source"]]
    # word index range of this piece within the long clip
    before = sum(len(q["text"].split()) for q in pieces if q["source"] == p["source"] and q["id"] < p["id"])
    s, e = float(p["start"]), float(p["end"])
    for k in range(before, before + len(words)):
        a, b = src[k]
        total += 1
        inside += (min(b, e) - max(a, s)) > 0  # the word's clip overlaps the piece's audio
# (3) R-0019 on the pieces
import ctranslate2
from transformers import WhisperProcessor
M = os.path.join(ROOT, "data/models/R-0019-int8")
proc = WhisperProcessor.from_pretrained(M)
m = ctranslate2.models.Whisper(M, device="cpu", compute_type="int8", intra_threads=8)
P = proc.tokenizer.convert_tokens_to_ids(["<|startoftranscript|>", "<|sw|>", "<|transcribe|>", "<|notimestamps|>"])
hyps = []
for p in pieces:
    x = sf.read(os.path.join(OUT, p["file"]), dtype="float32")[0]
    f = proc([x], sampling_rate=16000, return_tensors="np").input_features
    r = m.generate(ctranslate2.StorageView.from_array(np.ascontiguousarray(f)), [P], beam_size=5, max_length=225)
    hyps.append(proc.tokenizer.decode(r[0].sequences_ids[0], skip_special_tokens=True))
sc = score([p["text"] for p in pieces], hyps)
# edge check: are first/last words of pieces recognised as often as middle words?
edge_ok = sum(normalise(h).split()[:1] == p["text"].split()[:1] for p, h in zip(pieces, hyps) if normalise(h))
end_ok = sum(normalise(h).split()[-1:] == p["text"].split()[-1:] for p, h in zip(pieces, hyps) if normalise(h))
res = {"long_clips": len(rows), "pieces": len(pieces), "piece_seconds": [round(min(float(p["duration"]) for p in pieces), 1),
       round(float(np.median([float(p["duration"]) for p in pieces])), 1), round(max(float(p["duration"]) for p in pieces), 1)],
       "words_whose_clip_overlaps_their_piece": f"{inside}/{total}",
       "r0019_on_pieces": {"wer": round(sc["wer"], 2), "cer": round(sc["cer"], 2)},
       "first_word_right": f"{edge_ok}/{len(pieces)}", "last_word_right": f"{end_ok}/{len(pieces)}",
       "score_min_median": float(np.median([float(p["score_min"]) for p in pieces])),
       "score_mean_median": float(np.median([float(p["score_mean"]) for p in pieces]))}
json.dump(res, open(os.path.join(ROOT, "runs/R-0027/check_cutter.json"), "w"), indent=1)
print(json.dumps(res))
