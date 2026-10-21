"""Two decoding audits of a CTranslate2 (int8) model on a frozen clip list, on this laptop's CPU (no retraining).

candidates: does the right word survive beam search? Every clip is decoded twice with beam 5: once returning 1
  transcript (what Thetha does now) and once returning all 5. Reports the top choice, an optimistic ceiling (the best of
  the 5 per clip, chosen WITH the reference, so not an accuracy anyone can get), and the time cost. (R-0022, Codex's plan)
context: does a "my words" list help or harm? Decodes every clip with each list as previous text (<|startofprev|>),
  then counts list words that appear in the output but not in the reference, and decodes silence and quiet noise. (R-0023)

  CT2_USE_MKL=0 .venv/Scripts/python src/decode_audit.py candidates --clips runs/R-0022/clips.jsonl --out runs/R-0022
  CT2_USE_MKL=0 .venv/Scripts/python src/decode_audit.py context --clips runs/R-0022/clips.jsonl --out runs/R-0023 \
      --context "Thetha model twitter" --context "Ntlakanipho Johannesburg WhatsApp"
Clip list: one JSON per line with id and text; audio is data/nchlt_xho/audio/<speaker>/<id>.wav unless a "wav" path is given.
"""
import argparse
import json
import os
import sys
import time
from collections import Counter

import ctranslate2
import jiwer
import numpy as np
import soundfile as sf
from transformers import WhisperProcessor

sys.path.insert(0, os.path.dirname(__file__))
from scoring import NORMALISATION, normalise, score  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("mode", choices=["candidates", "context"])
ap.add_argument("--model", default="data/models/R-0019-int8")
ap.add_argument("--clips", required=True)
ap.add_argument("--root", default="data")
ap.add_argument("--beam-size", type=int, default=5, help="5 = the live page since R-0021")
ap.add_argument("--hypotheses", type=int, default=5)
ap.add_argument("--context", action="append", default=[], help="a word list, used as previous text (context mode)")
ap.add_argument("--max-new-tokens", type=int, default=96, help="96 = the NCHLT evaluations; fine for short clips")
ap.add_argument("--threads", type=int, default=8)
ap.add_argument("--out", required=True)
a = ap.parse_args()

clips = [json.loads(l) for l in open(a.clips, encoding="utf-8")]
proc = WhisperProcessor.from_pretrained(a.model)
tok = proc.tokenizer
m = ctranslate2.models.Whisper(a.model, device="cpu", compute_type="int8", intra_threads=a.threads)
PREFIX = tok.convert_tokens_to_ids(["<|startoftranscript|>", "<|sw|>", "<|transcribe|>", "<|notimestamps|>"])


def prompt(words=None):
    if not words:
        return PREFIX
    return [tok.convert_tokens_to_ids("<|startofprev|>")] + tok.encode(" " + words.strip(), add_special_tokens=False) + PREFIX


def features(audio):
    feats = proc([audio], sampling_rate=16000, return_tensors="np").input_features
    return ctranslate2.StorageView.from_array(np.ascontiguousarray(feats))


def decode(feats, p, n=1):
    """-> (list of n texts, seconds)."""
    t = time.time()
    r = m.generate(feats, [p], beam_size=a.beam_size, num_hypotheses=n, max_length=a.max_new_tokens)
    return [tok.decode(s, skip_special_tokens=True).strip() for s in r[0].sequences_ids], time.time() - t


def load(c):
    path = c.get("wav") or os.path.join(a.root, "nchlt_xho", "audio", c["speaker"], c["id"] + ".wav")
    audio, sr = sf.read(path, dtype="float32")
    assert sr == 16000, path
    return audio


def errors(ref, hyp):
    """(word errors, letter errors) of one clip, after normalisation."""
    ref, hyp = normalise(ref) or "-", normalise(hyp)
    w, c = jiwer.process_words(ref, hyp), jiwer.process_characters(ref, hyp)
    return w.substitutions + w.deletions + w.insertions, c.substitutions + c.deletions + c.insertions


def scores(rows, key):
    s = score([r["text"] for r in rows], [r[key] for r in rows])
    return {"wer": round(s["wer"], 2), "cer": round(s["cer"], 2), "clips": len(rows)}


os.makedirs(a.out, exist_ok=True)
rows, t0 = [], time.time()
for i, c in enumerate(clips):
    feats = features(load(c))
    row = {"id": c["id"], "text": c["text"], "text_in_training": c.get("text_in_training")}
    if a.mode == "candidates":
        # alternate the order so warm caches favour neither setting
        if i % 2:
            cands, row["secs_5"] = decode(feats, PREFIX, a.hypotheses)
            (row["hyp_1"],), row["secs_1"] = decode(feats, PREFIX)
        else:
            (row["hyp_1"],), row["secs_1"] = decode(feats, PREFIX)
            cands, row["secs_5"] = decode(feats, PREFIX, a.hypotheses)
        row["candidates"] = cands
        row["top"] = cands[0]
        row["best"] = min(cands, key=lambda h: errors(c["text"], h))  # uses the reference: a ceiling, not a result
        ref_words, top_words = Counter(normalise(c["text"]).split()), Counter(normalise(cands[0]).split())
        missing = ref_words - top_words
        others = set(w for h in cands[1:] for w in normalise(h).split())
        row["words_missing_from_top"] = sum(missing.values())
        row["missing_words_in_other_candidates"] = sum(n for w, n in missing.items() if w in others)
    else:
        for k, words in [("none", None)] + [(w, w) for w in a.context]:
            (row[k],), row["secs:" + k] = decode(feats, prompt(words))
    rows.append(row)
    if (i + 1) % 10 == 0:
        print(f"  {i + 1}/{len(clips)} clips, {time.time() - t0:.0f} s", flush=True)

with open(os.path.join(a.out, "predictions.jsonl"), "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

metrics = {"mode": a.mode, "model": a.model, "engine": f"ctranslate2 {ctranslate2.__version__} int8 CPU ({a.threads} threads)",
           "clips_file": a.clips, "clips": len(rows), "beam_size": a.beam_size, "max_new_tokens": a.max_new_tokens,
           "normalisation": NORMALISATION, "mkl": os.environ.get("CT2_USE_MKL", "default")}
groups = {"all": rows, "unseen": [r for r in rows if r["text_in_training"] == "unseen"]}
if a.mode == "candidates":
    metrics["hypotheses"] = a.hypotheses
    for g, rs in groups.items():
        if not rs:
            continue
        top, one, best = scores(rs, "top"), scores(rs, "hyp_1"), scores(rs, "best")
        metrics[g] = {"returning_1": one, "top_of_5": top, "best_of_5_ceiling": best,
                      "ceiling_wer_gain": round(top["wer"] - best["wer"], 2),
                      "top_wrong_but_a_candidate_exact": sum(normalise(r["top"]) != normalise(r["text"])
                                                             and normalise(r["best"]) == normalise(r["text"]) for r in rs),
                      "top_wrong": sum(normalise(r["top"]) != normalise(r["text"]) for r in rs),
                      "words_missing_from_top": sum(r["words_missing_from_top"] for r in rs),
                      "of_which_in_another_candidate": sum(r["missing_words_in_other_candidates"] for r in rs)}
    metrics["top_same_as_returning_1"] = sum(normalise(r["top"]) == normalise(r["hyp_1"]) for r in rows)
    metrics["seconds_returning_1"] = round(sum(r["secs_1"] for r in rows), 1)
    metrics["seconds_returning_5"] = round(sum(r["secs_5"] for r in rows), 1)
    metrics["time_ratio"] = round(metrics["seconds_returning_5"] / metrics["seconds_returning_1"], 3)
    ceiling, top = metrics["all"]["ceiling_wer_gain"], metrics["all"]
    metrics["pass"] = (ceiling >= 3 and top["top_of_5"]["wer"] <= top["returning_1"]["wer"]
                       and top["top_of_5"]["cer"] <= top["returning_1"]["cer"] and metrics["time_ratio"] <= 1.25)
else:
    metrics["contexts"] = a.context
    for g, rs in groups.items():
        if rs:
            metrics[g] = {k: scores(rs, k) for k in ["none"] + a.context}
    metrics["false_insertions"] = {}
    for w in a.context:
        listed = set(normalise(w).split())
        n = 0
        for r in rows:
            extra = Counter(normalise(r[w]).split()) - Counter(normalise(r["text"]).split())
            n += sum(v for k, v in extra.items() if k in listed)
        metrics["false_insertions"][w] = n
    metrics["seconds"] = {k: round(sum(r["secs:" + k] for r in rows), 1) for k in ["none"] + a.context}
    # silence and quiet noise: the right output is nothing
    rng = np.random.default_rng(1)
    tests = {"silence 5 s": np.zeros(80000, np.float32), "quiet noise 5 s": (rng.standard_normal(80000) * 0.003).astype(np.float32)}
    metrics["empty_audio"] = {name: {k: decode(features(x), prompt(w))[0][0] for k, w in [("none", None)] + [(w, w) for w in a.context]}
                              for name, x in tests.items()}
json.dump(metrics, open(os.path.join(a.out, "metrics.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(metrics, ensure_ascii=False))
