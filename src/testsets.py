"""The four test sets, loaded and reported the same way by every evaluator, so their scores compare clip for clip.

Used by src/baseline.py (transformers, greedy), src/eval_guarded.py (faster-whisper with Whisper's reliability rules,
R-0033) and src/eval_omni.py (Meta Omnilingual CTC, R-0034). One test set per call:
  NCHLT      --xml data/nchlt_xho/transcriptions/nchlt_xho.tst.xml --root data
  FLEURS     --fleurs-tsv data/fleurs_xh_za/test.tsv --fleurs-audio data/fleurs_xh_za/audio/test
  Swivuriso  --swivuriso-tsv data/swivuriso_16k/dev_test.tsv --swivuriso-audio data/swivuriso_16k
  Soapies    --soapies-root data/soapies_engxho [--soapies-split tst]   (research-only data, D-0016)
Clips over --max-seconds (30) are left out, as in every earlier run (Whisper hears 30 s at most). --sample N keeps a
seeded random N of them (the same N clips for every model, e.g. for CPU timing). Every evaluator writes the same three
files to --out: predictions.jsonl, metrics.json, samples.md (the format src/compare_runs.py reads).
"""
import collections
import json
import os
import random
from math import gcd

import fleurs
import nchlt
import soapies
import swivuriso
from scoring import NORMALISATION, normalise, score

# The token limits every earlier evaluation used per test set (R-0019/R-0029 job.sh, eval_soapies.py): kept as the
# defaults so that a new decoder is the only change. Whisper can write at most 448 tokens, 4 of them the prompt.
DEFAULT_MAX_NEW_TOKENS = {"nchlt": 96, "fleurs": 225, "swivuriso": 440, "soapies": 96}


def add_args(ap):
    ap.add_argument("--xml", help="NCHLT test transcription XML")
    ap.add_argument("--root", default="data", help="folder the NCHLT XML's audio paths are relative to")
    ap.add_argument("--fleurs-tsv", help="FLEURS split .tsv (instead of --xml)")
    ap.add_argument("--fleurs-audio", help="folder holding that FLEURS split's .wav files")
    ap.add_argument("--swivuriso-tsv", help="Swivuriso split .tsv from src/swivuriso.py (instead of --xml)")
    ap.add_argument("--swivuriso-audio", help="folder that TSV's file paths are relative to")
    ap.add_argument("--soapies-root", help="Soapies engxho folder (balanced_engxho.xml, ids/, extracted/)")
    ap.add_argument("--soapies-split", default="tst", help="tst | dev")
    ap.add_argument("--train-xml", help="training split; adds scores on test clips whose sentence never occurs in training")
    ap.add_argument("--train-fleurs-tsv", help="FLEURS training .tsv, also counted as 'seen in training'")
    ap.add_argument("--max-seconds", type=float, default=30.0,
                    help="leave out longer clips: Whisper only hears the first 30 s, so scoring them would be unfair")
    ap.add_argument("--limit", type=int, default=0, help="only the first N clips (0 = all)")
    ap.add_argument("--sample", type=int, default=0, help="a seeded random N of the clips (0 = all); same N clips "
                    "for every model and evaluator with the same --sample-seed")
    ap.add_argument("--sample-seed", type=int, default=1)
    ap.add_argument("--samples", type=int, default=20, help="clips shown in samples.md")
    ap.add_argument("--seed", type=int, default=1, help="seed for the samples.md pick")


def kind_of(a):
    given = [k for k, v in (("nchlt", a.xml), ("fleurs", a.fleurs_tsv), ("swivuriso", a.swivuriso_tsv),
                            ("soapies", getattr(a, "soapies_root", None))) if v]
    if len(given) != 1:
        raise SystemExit("give exactly one of --xml, --fleurs-tsv, --swivuriso-tsv or --soapies-root")
    return given[0]


def test_set_name(a, kind):
    if kind == "soapies":
        return f"soapies engxho {a.soapies_split}"
    return os.path.basename(a.xml or a.fleurs_tsv or a.swivuriso_tsv)


def load(a):
    """-> (kind, clips, too_long). Clips keep the loaders' fields (id, speaker, gender, path, duration, text, ...)."""
    kind = kind_of(a)
    if kind == "nchlt":
        clips = nchlt.load_split(a.xml, a.root)
    elif kind == "fleurs":
        clips = fleurs.load_split(a.fleurs_tsv, a.fleurs_audio or "")
    elif kind == "swivuriso":
        clips = swivuriso.load_split(a.swivuriso_tsv, a.swivuriso_audio or "")
    else:
        R = a.soapies_root
        clips = soapies.load_split(os.path.join(R, "balanced_engxho.xml"),
                                   os.path.join(R, "ids", "cs_engxho_balanced", "transcriptions",
                                                f"engxho_{a.soapies_split}_set_utterance_ids.txt"),
                                   os.path.join(R, "extracted"))
        missing = [c["id"] for c in clips if not c["path"]]
        assert not missing, f"{len(missing)} Soapies clips have no audio file, e.g. {missing[:3]}"
        for c in clips:
            c["gender"] = ""
    too_long = [c for c in clips if c["duration"] > a.max_seconds]
    clips = [c for c in clips if c["duration"] <= a.max_seconds]
    if too_long:
        print(f"left out {len(too_long)} clips over {a.max_seconds:.0f} s", flush=True)
    if a.limit:
        clips = clips[: a.limit]
    if getattr(a, "sample", 0):
        keep = set(random.Random(a.sample_seed).sample(range(len(clips)), min(a.sample, len(clips))))
        clips = [c for i, c in enumerate(clips) if i in keep]  # original order kept
    print(f"{len(clips)} clips, {sum(c['duration'] for c in clips) / 3600:.2f} h, "
          f"{len({c['speaker'] for c in clips})} speakers", flush=True)
    return kind, clips, too_long


def read16k(path):
    """Audio file -> 16 kHz mono float32 (NCHLT, FLEURS and Swivuriso are 16 kHz already; Soapies is 32 kHz)."""
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly

    audio, sr = sf.read(path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != 16000:
        g = gcd(sr, 16000)
        audio = resample_poly(audio, 16000 // g, sr // g).astype("float32")
    return np.ascontiguousarray(audio, dtype=np.float32)


def _soapies_extras(clips):
    """R-0030's diagnostics: share of each language's reference words heard, and CER ignoring spaces."""
    import jiwer

    def hits(c, lang):
        ref = collections.Counter(w for l, t in c["segments"] if l == lang for w in normalise(t).split())
        got = collections.Counter(normalise(c["hyp"]).split())
        return sum(min(n, got[w]) for w, n in ref.items()), sum(ref.values())

    out = {"cer_no_spaces": round(100 * jiwer.cer([normalise(c["text"]).replace(" ", "") for c in clips],
                                                  [normalise(c["hyp"]).replace(" ", "") or "-" for c in clips]), 2)}
    words = {}
    for lang in ("eng", "xho"):
        h, n = map(sum, zip(*(hits(c, lang) for c in clips)))
        words[lang] = {"hit": h, "words": n, "pct": round(100 * h / n, 1) if n else None}
    out["word_hits"] = words
    return out


def runaway(ref, hyp):
    """A runaway output (Neon pre-flight memo): over 2.5x the reference's length and over 150 letters."""
    return len(hyp) > 2.5 * len(ref) and len(hyp) > 150


def diagnostics(kind, clips):
    """Secondary views of the same predictions, for fair comparisons between very different models (R-0033/R-0034).
    The headline WER/CER stay the plain scoring.normalise scores."""
    import jiwer

    def sub(name, rows):
        if not rows:
            return {name: None}
        s = score([c["text"] for c in rows], [c["hyp"] for c in rows])
        return {name: {"wer": round(s["wer"], 2), "cer": round(s["cer"], 2), "n": s["n"]}}

    out = {"cer_no_spaces": round(100 * jiwer.cer([normalise(c["text"]).replace(" ", "") or "-" for c in clips],
                                                  [normalise(c["hyp"]).replace(" ", "") or "-" for c in clips]), 2),
           "runaway_clips": sum(runaway(normalise(c["text"]), normalise(c["hyp"])) for c in clips),
           "outputs_with_digits": sum(any(ch.isdigit() for ch in c["hyp"]) for c in clips),
           "outputs_with_non_ascii": sum(any(ord(ch) > 127 for ch in c["hyp"]) for c in clips)}
    if kind == "fleurs":  # 200 of 1034 FLEURS test references contain digits; a spelled-out number scores as wrong
        out.update(sub("reference_without_digits", [c for c in clips if not any(ch.isdigit() for ch in c["text"])]))
        out.update(sub("reference_with_digits", [c for c in clips if any(ch.isdigit() for ch in c["text"])]))
    return out


def report(a, kind, clips, too_long, *, model, language, max_new_tokens, seconds, env, extra=None,
           column="Whisper's language", output_column="Whisper's output"):
    """Score clips (each has "hyp" and "lang") and write predictions.jsonl, metrics.json and samples.md to a.out.
    The metrics keys and order are those src/baseline.py always wrote; `extra` is appended after them."""
    os.makedirs(a.out, exist_ok=True)
    seen = set()
    if a.train_xml:
        seen |= {normalise(c["text"]) for c in nchlt.load_split(a.train_xml, a.root)}
    if a.train_fleurs_tsv:
        seen |= {normalise(c["text"]) for c in fleurs.load_split(a.train_fleurs_tsv, "")}
    for c in clips:
        c["text_in_training"] = "seen" if normalise(c["text"]) in seen else "unseen"
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
    metrics = {
        "model": model, "language": language, "test_set": test_set_name(a, kind),
        "clips": len(clips), "left_out_over_max_seconds": len(too_long), "max_new_tokens": max_new_tokens,
        "audio_hours": round(sum(c["duration"] for c in clips) / 3600, 3),
        "wer": round(total["wer"], 2), "cer": round(total["cer"], 2),
        "exact_match_pct": round(100 * sum(c["exact"] for c in clips) / len(clips), 2),
        "empty_output_pct": round(100 * sum(not normalise(c["hyp"]) for c in clips) / len(clips), 2),
        "detected_languages": dict(collections.Counter(c["lang"] for c in clips).most_common()),
        "per_speaker": group("speaker"), "per_gender": group("gender"),
        **({"by_text_in_training": group("text_in_training")} if (a.train_xml or a.train_fleurs_tsv) else {}),
        **({"per_type": group("type")} if kind == "swivuriso" else {}),  # scripted (read) vs unscripted (own words)
        **({"per_languages": group("langs"), **_soapies_extras(clips)} if kind == "soapies" else {}),
        "normalisation": NORMALISATION, "seconds": round(seconds, 1),
        **(extra or {}),
        "env": env,
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
        f.write(f"# Samples: {model}, language={language}\n\n")
        f.write(f"| clip | speaker | {column} | reference | {output_column} | WER % | CER % |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for c in picks:
            f.write(f"| {c['id']} | {c['speaker']} {(c['gender'] or '-')[0]} | {c['lang']} | {c['text']} | "
                    f"{c['hyp'].replace('|', '/')} | {c['wer']} | {c['cer']} |\n")
    return metrics
