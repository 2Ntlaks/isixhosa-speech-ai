"""R-0027 quality gate for the cut Swivuriso long-clip pieces, run on the node before any training.

R-0019 (never trained on these clips: they were over 30 s) transcribed a random sample of pieces. A badly cut piece
shows up as extra or missing words at its edges, so R-0019's error on it jumps. Pieces are grouped into five equal
bands by their weakest word's alignment score; the lowest band whose CER and every band above it are at most
MAX_CER sets the threshold. Keeps every piece at or above it. Exits 1 (no training) if the kept sample's CER is above
MAX_CER or fewer than MIN_HOURS remain.

  python runs/R-0027/gate.py pieces.tsv sample_predictions.jsonl out_train_pieces.tsv gate.json
"""
import csv
import json
import sys

sys.path.insert(0, "src")
from scoring import normalise, score  # noqa: E402

MAX_CER, MIN_HOURS = 8.0, 20.0
pieces_tsv, preds_jsonl, out_tsv, out_json = sys.argv[1:5]
csv.field_size_limit(10 ** 8)
with open(pieces_tsv, encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f, delimiter="\t")
    fields, pieces = reader.fieldnames, list(reader)
by_id = {p["id"]: p for p in pieces}
preds = [json.loads(l) for l in open(preds_jsonl, encoding="utf-8")]
sample = sorted(((by_id[r["id"].removeprefix("swiv_")], r) for r in preds), key=lambda x: float(x[0]["score_min"]))

bands, k = [], len(sample)
for b in range(5):
    part = sample[b * k // 5:(b + 1) * k // 5]
    sc = score([r["text"] for _, r in part], [r["hyp"] for _, r in part])
    bands.append({"score_min_from": float(part[0][0]["score_min"]), "clips": len(part), "cer": round(sc["cer"], 2),
                  "wer": round(sc["wer"], 2)})
start = next((b for b in range(5) if all(x["cer"] <= MAX_CER for x in bands[b:])), None)
threshold = bands[start]["score_min_from"] if start is not None else float("inf")
kept_sample = [(p, r) for p, r in sample if float(p["score_min"]) >= threshold]


def edge(rows, side):
    ok = sum((normalise(r["hyp"]).split() or [""])[side] == p["text"].split()[side] for p, r in rows)
    return round(100 * ok / max(1, len(rows)), 1)


kept = [p for p in pieces if float(p["score_min"]) >= threshold]
hours = sum(float(p["duration"]) for p in kept) / 3600
sc = score([r["text"] for _, r in kept_sample], [r["hyp"] for _, r in kept_sample]) if kept_sample else {"cer": 100, "wer": 100}
result = {"max_cer": MAX_CER, "min_hours": MIN_HOURS, "bands": bands, "score_min_threshold": threshold,
          "sample": len(sample), "kept_sample": len(kept_sample),
          "kept_sample_cer": round(sc["cer"], 2), "kept_sample_wer": round(sc["wer"], 2),
          "first_word_right_pct": edge(kept_sample, 0), "last_word_right_pct": edge(kept_sample, -1),
          "pieces": len(pieces), "pieces_kept": len(kept), "hours_kept": round(hours, 2),
          "hours_by_type": {t: round(sum(float(p["duration"]) for p in kept if p["type"] == t) / 3600, 2)
                            for t in sorted({p["type"] for p in kept})}}
result["pass"] = bool(kept_sample) and sc["cer"] <= MAX_CER and hours >= MIN_HOURS
with open(out_tsv, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fields, delimiter="\t")
    w.writeheader()
    w.writerows(kept)
json.dump(result, open(out_json, "w"), indent=1)
print(json.dumps(result, indent=1))
sys.exit(0 if result["pass"] else 1)
