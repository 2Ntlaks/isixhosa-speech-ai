"""Tiny synthetic copies of the four test-set formats (NCHLT XML, FLEURS TSV, Swivuriso TSV, Soapies XML + id lists),
plus NCHLT/FLEURS/Swivuriso training and dev files, for tests that must run without the real data.

Audio is tones and noise; transcripts are placeholder English words (never invented isiXhosa). Deterministic.
  python tests/fixture_data.py <folder>      (or import build)
"""
import csv
import os
import sys

import numpy as np
import soundfile as sf

WORDS = "alpha beta gamma delta echo foxtrot golf hotel india juliet kilo lima mike november oscar papa".split()


def _wav(path, seconds, seed, sr=16000):
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * sr)) / sr
    audio = 0.1 * np.sin(2 * np.pi * (200 + 40 * (seed % 7)) * t) + 0.01 * rng.standard_normal(len(t))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sf.write(path, audio.astype("float32"), sr, subtype="PCM_16")
    return len(audio) / sr


def _text(i, n=4):
    return " ".join(WORDS[(i * 3 + k) % len(WORDS)] for k in range(n))


def nchlt(root, split, speakers, per_speaker, seed0):
    """root/nchlt_xho/transcriptions/nchlt_xho.<split>.xml with audio under root/nchlt_xho/audio/<spk>/."""
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<corpus>"]
    k = seed0
    for s, (spk, gender) in enumerate(speakers):
        lines.append(f'<speaker id="{spk}" gender="{gender}">')
        for j in range(per_speaker):
            k += 1
            rel = f"nchlt_xho/audio/{spk}/nchlt_xho_{spk}{gender[0]}_{j:04d}.wav"
            dur = _wav(os.path.join(root, rel), 1.0 + (k % 3) * 0.5, k)
            lines.append(f'<recording audio="{rel}" duration="{dur:.3f}"><orth>{_text(k)} [s]</orth></recording>')
        lines.append("</speaker>")
    lines.append("</corpus>")
    path = os.path.join(root, "nchlt_xho", "transcriptions", f"nchlt_xho.{split}.xml")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    return path


def fleurs(root, split, n, seed0, long_clip=False):
    folder = os.path.join(root, "fleurs_xh_za")
    rows = []
    for j in range(n):
        k = seed0 + j
        name = f"{k}.wav"
        dur = _wav(os.path.join(folder, "audio", split, name), 31.0 if (long_clip and j == 0) else 2.0 + (k % 4), k)
        text = _text(k, 6)
        rows.append([str(k), name, text.capitalize() + ".", text, "x", str(int(dur * 16000)), "MALE" if k % 2 else "FEMALE"])
    path = os.path.join(folder, f"{split}.tsv")
    with open(path, "w", encoding="utf-8", newline="") as f:
        csv.writer(f, delimiter="\t", quoting=csv.QUOTE_NONE, escapechar="\\").writerows(rows)
    return path


def swivuriso(root, split, n, seed0, speakers=3):
    folder = os.path.join(root, "swivuriso_16k")
    rows = []
    for j in range(n):
        k = seed0 + j
        rel = f"{split}/clip{k}.wav"
        dur = _wav(os.path.join(folder, rel), 1.5 + (k % 5), k)
        text = _text(k, 5)
        rows.append({"id": f"clip{k}", "speaker": f"spk{split}{j % speakers}", "type": "scripted" if k % 2 else "unscripted",
                     "domain": "test", "duration": f"{dur:.3f}", "file": rel, "text": text, "raw": text})
    path = os.path.join(folder, f"{split}.tsv")
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, ["id", "speaker", "type", "domain", "duration", "file", "text", "raw"], delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    return path


def soapies(root, n, seed0):
    folder = os.path.join(root, "soapies_engxho")
    utts, ids = [], []
    for j in range(n):
        k = seed0 + j
        uid = f"soap_{k:04d}"
        dur = _wav(os.path.join(folder, "extracted", "wavs", uid + ".wav"), 2.0 + (k % 3), k, sr=32000)
        utts.append(f"<utterance><audio>{uid}.wav</audio><speaker_id>sp{j % 2}</speaker_id>"
                    f"<duration>{int(dur * 1000)}</duration>"
                    f"<utterance_segment><lang_id>eng</lang_id><transcription>{_text(k, 2)}</transcription></utterance_segment>"
                    f"<utterance_segment><lang_id>xho</lang_id><transcription>{_text(k + 1, 2)}</transcription></utterance_segment>"
                    "</utterance>")
        ids.append(uid)
    open(os.path.join(folder, "balanced_engxho.xml"), "w", encoding="utf-8").write("<corpus>" + "".join(utts) + "</corpus>")
    idp = os.path.join(folder, "ids", "cs_engxho_balanced", "transcriptions")
    os.makedirs(idp, exist_ok=True)
    open(os.path.join(idp, "engxho_tst_set_utterance_ids.txt"), "w").write("\n".join(ids) + "\n")
    open(os.path.join(idp, "engxho_dev_set_utterance_ids.txt"), "w").write("\n".join(ids[:2]) + "\n")
    return folder


def build(root, n=6):
    """All fixture files under root. Returns a dict of the paths the evaluators and train.py take."""
    spk_train = [(f"{i:03d}", "female" if i % 2 else "male") for i in range(1, 9)]
    spk_test = [("101", "female"), ("102", "male")]
    p = {
        "root": root,
        "nchlt_train": nchlt(root, "trn", spk_train, 3, 0),
        "nchlt_test": nchlt(root, "tst", spk_test, n // 2, 500),
        "fleurs_train": fleurs(root, "train", n, 1000),
        "fleurs_dev": fleurs(root, "dev", n, 2000),
        "fleurs_test": fleurs(root, "test", n, 3000, long_clip=True),
        "swiv_train": swivuriso(root, "train", 2 * n, 4000),
        "swiv_dev": swivuriso(root, "dev", n, 5000),
        "swiv_test": swivuriso(root, "dev_test", n, 6000),
        "soapies": soapies(root, n, 7000),
    }
    p["fleurs_audio"] = os.path.join(root, "fleurs_xh_za", "audio")
    p["swiv_audio"] = os.path.join(root, "swivuriso_16k")
    return p


if __name__ == "__main__":
    print(build(sys.argv[1]))
