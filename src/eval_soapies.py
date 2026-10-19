"""Score a CTranslate2 (int8) model on the Soapies English-isiXhosa code-switched test set, on this laptop's CPU.
Stage 4's yardstick: real mixed isiXhosa + English speech from TV soap operas (research-only data, D-0016).

  CT2_USE_MKL=0 .venv/Scripts/python src/eval_soapies.py --model data/models/R-0012-int8 --lang sw \
      --out runs/R-0014/R-0012
--lang sw  : the prompt our fine-tunes were trained with (<|sw|> stands for isiXhosa, D-0007)
--lang auto: let Whisper pick the language per clip (the stock-model "before" picture, like R-0001)
Greedy decoding, no timestamps, 96-token limit (as on NCHLT). Besides WER/CER it reports two diagnostics:
- English / isiXhosa word hits: share of the reference words of each language's segments that appear in the output
  (bag of words, so order is ignored). Shows which half of the mixed speech a model gets.
- CER without spaces: forgives word-splitting differences (i grapefruit vs igrapefruit vs i-grapefruit).
Writes predictions.jsonl and metrics.json to --out.
"""
import argparse
import collections
import json
import os
import sys
import time
from math import gcd

import ctranslate2
import jiwer
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from transformers import WhisperProcessor

sys.path.insert(0, os.path.dirname(__file__))
from scoring import NORMALISATION, normalise, score  # noqa: E402
from soapies import load_split  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--lang", default="sw", help="sw | en | auto")
ap.add_argument("--root", default="data/soapies_engxho")
ap.add_argument("--split", default="tst", help="tst | dev")
ap.add_argument("--max-new-tokens", type=int, default=96)
ap.add_argument("--threads", type=int, default=8)
ap.add_argument("--out", required=True)
a = ap.parse_args()

clips = load_split(os.path.join(a.root, "balanced_engxho.xml"),
                   os.path.join(a.root, "ids", "cs_engxho_balanced", "transcriptions",
                                f"engxho_{a.split}_set_utterance_ids.txt"),
                   os.path.join(a.root, "extracted"))
missing = [c["id"] for c in clips if not c["path"]]
assert not missing, f"{len(missing)} clips have no audio file, e.g. {missing[:3]}"

proc = WhisperProcessor.from_pretrained(a.model)
m = ctranslate2.models.Whisper(a.model, device="cpu", compute_type="int8", intra_threads=a.threads)
tok = proc.tokenizer.convert_tokens_to_ids


def word_hits(segs, hyp, lang):
    ref = collections.Counter(w for l, t in segs if l == lang for w in normalise(t).split())
    got = collections.Counter(normalise(hyp).split())
    return sum(min(n, got[w]) for w, n in ref.items()), sum(ref.values())


os.makedirs(a.out, exist_ok=True)
out, langs_seen, t0 = [], collections.Counter(), time.time()
for i, c in enumerate(clips):
    audio, sr = sf.read(c["path"], dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != 16000:
        g = gcd(sr, 16000)
        audio = resample_poly(audio, 16000 // g, sr // g).astype("float32")
    feats = ctranslate2.StorageView.from_array(np.ascontiguousarray(
        proc([audio], sampling_rate=16000, return_tensors="np").input_features))
    lang = a.lang
    if lang == "auto":
        lang = m.detect_language(feats)[0][0][0].strip("<|>")
    langs_seen[lang] += 1
    prompt = tok(["<|startoftranscript|>", f"<|{lang}|>", "<|transcribe|>", "<|notimestamps|>"])
    r = m.generate(feats, [prompt], beam_size=1, max_length=a.max_new_tokens)
    hyp = proc.tokenizer.decode(r[0].sequences_ids[0], skip_special_tokens=True)
    out.append({"id": c["id"], "speaker": c["speaker"], "langs": c["langs"], "lang_prompt": lang,
                "text": c["text"], "hyp": hyp, "segments": c["segments"]})
    if (i + 1) % 50 == 0:
        print(f"  {i + 1}/{len(clips)} clips, {time.time() - t0:.0f} s", flush=True)
secs = time.time() - t0

with open(os.path.join(a.out, "predictions.jsonl"), "w", encoding="utf-8") as f:
    for o in out:
        f.write(json.dumps(o, ensure_ascii=False) + "\n")
s = score([o["text"] for o in out], [o["hyp"] for o in out])
nospace = 100 * jiwer.cer([normalise(o["text"]).replace(" ", "") for o in out],
                          [normalise(o["hyp"]).replace(" ", "") or "-" for o in out])
hits = {}
for lang in ("eng", "xho"):
    h, n = map(sum, zip(*(word_hits(o["segments"], o["hyp"], lang) for o in out)))
    hits[lang] = {"hit": h, "words": n, "pct": round(100 * h / n, 1)}
metrics = {"model": a.model, "lang": a.lang, "langs_used": dict(langs_seen), "test_set": f"soapies engxho {a.split}",
           "clips": len(out), "speakers": len({o["speaker"] for o in out}),
           "audio_minutes": round(sum(c["duration"] for c in clips) / 60, 1),
           "wer": round(s["wer"], 2), "cer": round(s["cer"], 2), "cer_no_spaces": round(nospace, 2),
           "word_hits": hits, "exact": sum(normalise(o["text"]) == normalise(o["hyp"]) for o in out),
           "engine": f"ctranslate2 {ctranslate2.__version__} int8 CPU ({a.threads} threads)",
           "seconds_per_clip": round(secs / len(out), 2), "normalisation": NORMALISATION,
           "mkl": os.environ.get("CT2_USE_MKL", "default")}
json.dump(metrics, open(os.path.join(a.out, "metrics.json"), "w"), indent=1)
print(json.dumps(metrics))
