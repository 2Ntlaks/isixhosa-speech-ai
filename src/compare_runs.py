"""Compare evaluation runs clip by clip (same test set): headline scores, seen/unseen split, per speaker,
isiXhosa letter patterns, and the same sample clips side by side.

  python src/compare_runs.py runs/R-0001 runs/R-0003 runs/R-0004 > runs/R-0004/comparison.json
  python src/compare_runs.py R-0019-greedy=runs/R-0019/eval_fleurs R-0019-guarded=runs/R-0033/gpu_fp16/eval_fleurs
Each run folder must contain predictions.jsonl and metrics.json (src/baseline.py, src/eval_guarded.py,
src/eval_omni.py, or the older src/eval_soapies.py / src/eval_ct2.py). A folder is named by the run ID in its path,
or by NAME= in front of it (needed when several folders belong to one run).
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
    args = sys.argv[1:]
    named = [a.split("=", 1) if "=" in a and not os.path.isdir(a) else (None, a) for a in args]
    folders = [f for _, f in named]
    def name(label, f):  # run ID: runs/R-0012/eval_fleurs -> R-0012 (P-0010: several folders are called eval_*)
        if label:
            return label
        parts = os.path.normpath(f).split(os.sep)
        return next((x for x in reversed(parts) if x.startswith("R-")), parts[-1])
    runs = {name(label, f): load(f) for label, f in named}
    assert len(runs) == len(folders), "two folders map to the same run name"
    ids = sorted(set.intersection(*(set(p) for p, _ in runs.values())))
    report = {"clips_compared": len(ids), "runs": {}}
    for name, (preds, metrics) in runs.items():
        sub = [preds[i] for i in ids]
        per_speaker = metrics.get("per_speaker")
        if per_speaker is None and all("speaker" in p for p in sub):  # older evaluators did not group by speaker
            per_speaker = {s: {"cer": round(score([p["text"] for p in sub if p["speaker"] == s],
                                                  [p["hyp"] for p in sub if p["speaker"] == s])["cer"], 1)}
                           for s in sorted({p["speaker"] for p in sub})}
        report["runs"][name] = {
            "model": metrics["model"], "language": metrics.get("language", metrics.get("lang")),
            "wer": metrics["wer"], "cer": metrics["cer"],
            "exact_match_pct": metrics.get("exact_match_pct",
                                           round(100 * sum(normalise(p["text"]) == normalise(p["hyp"]) for p in sub)
                                                 / len(sub), 2)),
            "by_text_in_training": metrics.get("by_text_in_training"),
            "per_speaker_cer": {k: v["cer"] for k, v in (per_speaker or {}).items()},
            **({"guard": {k: v for k, v in metrics["guard"].items() if k != "fallback_clips"}}
               if "guard" in metrics else {}),
            "patterns": pattern_recall({p["id"]: p for p in sub}),
            "check": score([p["text"] for p in sub], [p["hyp"] for p in sub]),
        }
    # the 20 sample clips first shown in R-0001's samples.md, so every run is compared on the same audio
    first = folders[0]
    samples_md = os.path.join(first, "samples.md")  # src/eval_soapies.py and src/eval_ct2.py never wrote one
    sample_ids = [line.split("|")[1].strip() for line in open(samples_md, encoding="utf-8")
                  if line.startswith(("| nchlt_", "| fleurs_"))] if os.path.isfile(samples_md) else []
    report["samples"] = [{"id": i, "speaker": runs[next(iter(runs))][0][i]["speaker"],
                          "reference": runs[next(iter(runs))][0][i]["text"],
                          **{name: {"hyp": p[i]["hyp"], "cer": p[i]["cer"]} for name, (p, _) in runs.items()}}
                         for i in sample_ids if all(i in p for p, _ in runs.values())]
    json.dump(report, sys.stdout, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
