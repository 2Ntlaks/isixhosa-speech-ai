"""Compare evaluation runs clip by clip (same test set): headline scores, seen/unseen split, per speaker,
isiXhosa letter patterns, and the same sample clips side by side.

  python src/compare_runs.py runs/R-0001 runs/R-0003 runs/R-0004 > runs/R-0004/comparison.json
Each run folder must contain predictions.jsonl and metrics.json (as written by src/baseline.py).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from scoring import normalise, score  # noqa: E402

PATTERNS = ["kh", "th", "hl", "dl", "x", "q", "c", "ng"]


def load(folder):
    preds = [json.loads(l) for l in open(os.path.join(folder, "predictions.jsonl"), encoding="utf-8")]
    return {p["id"]: p for p in preds}, json.load(open(os.path.join(folder, "metrics.json"), encoding="utf-8"))


def pattern_recall(preds):
    """For each pattern: how often the reference has it, and how often the output has it in the same clip (capped)."""
    out = {}
    for pat in PATTERNS:
        ref = hit = 0
        for p in preds.values():
            r, h = normalise(p["text"]).count(pat), normalise(p["hyp"]).count(pat)
            ref += r
            hit += min(r, h)
        out[pat] = {"in_reference": ref, "matched": hit, "pct": round(100 * hit / ref, 1) if ref else None}
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # outputs include Arabic, Hindi, Khmer script
    folders = sys.argv[1:]
    runs = {os.path.basename(f.rstrip("/")): load(f) for f in folders}
    ids = sorted(set.intersection(*(set(p) for p, _ in runs.values())))
    report = {"clips_compared": len(ids), "runs": {}}
    for name, (preds, metrics) in runs.items():
        sub = [preds[i] for i in ids]
        report["runs"][name] = {
            "model": metrics["model"], "language": metrics["language"],
            "wer": metrics["wer"], "cer": metrics["cer"], "exact_match_pct": metrics["exact_match_pct"],
            "by_text_in_training": metrics.get("by_text_in_training"),
            "per_speaker_cer": {k: v["cer"] for k, v in metrics["per_speaker"].items()},
            "patterns": pattern_recall({p["id"]: p for p in sub}),
            "check": score([p["text"] for p in sub], [p["hyp"] for p in sub]),
        }
    # the 20 sample clips first shown in R-0001's samples.md, so every run is compared on the same audio
    first = folders[0]
    sample_ids = [line.split("|")[1].strip() for line in open(os.path.join(first, "samples.md"), encoding="utf-8")
                  if line.startswith(("| nchlt_", "| fleurs_"))]
    report["samples"] = [{"id": i, "speaker": runs[next(iter(runs))][0][i]["speaker"],
                          "reference": runs[next(iter(runs))][0][i]["text"],
                          **{name: {"hyp": p[i]["hyp"], "cer": p[i]["cer"]} for name, (p, _) in runs.items()}}
                         for i in sample_ids if all(i in p for p, _ in runs.values())]
    json.dump(report, sys.stdout, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
