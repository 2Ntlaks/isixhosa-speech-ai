"""Fine-tune Whisper on the NCHLT isiXhosa training split, optionally plus FLEURS (--fleurs-tsv/--fleurs-audio).

  python src/train.py --xml data/nchlt_xho/transcriptions/nchlt_xho.trn.xml --root data --out out/model \
      --model openai/whisper-small --language sw --max-steps 4000

- isiXhosa borrows Swahili's language tag (D-0007): every training target starts <|startoftranscript|><|sw|><|transcribe|>.
- A few training speakers are held out as a dev set to pick the best checkpoint; the 8 test speakers are never touched here.
- Checkpoints go to <out>/checkpoints/; if one exists the run resumes from it (survives a restarted machine).
- The best checkpoint (lowest dev CER) is saved to <out>/final with its processor, ready for src/baseline.py.
Stage 3 more data (D-0024): --swivuriso-tsv/--swivuriso-audio add Swivuriso clips prepared by src/swivuriso.py;
--exclude-texts drops any of them whose sentence is in a test set.
Stage 4 (code-switching, D-0016/D-0017), all optional:
- --english-xml: NCHLT English training clips (--english-hours of them), learned with Whisper's own <|en|> tag.
- --stitch N: N clips made by joining a real NCHLT isiXhosa clip and a real NCHLT English clip (x+e, e+x or x+e+x,
  with a short silence between). Transcripts are the corpora's own; learned with the isiXhosa tag. Teaches the model
  to keep English words in English spelling inside isiXhosa speech.
- --soapies-root: score the Soapies code-switched dev set at each evaluation and pick the best checkpoint on it
  (research-only data: dev/test use only, never trained on).
Training recipe options (R-0035, D-0031); every default reproduces the earlier runs exactly:
- --epochs E: train for E passes over the training clips instead of --max-steps (rounded up to a whole number of
  --eval-every, so the last steps are evaluated and saved); --lr-scheduler linear (default) | cosine | ...
- --swivuriso-dev-tsv/--swivuriso-dev-audio: also score Swivuriso dev clips at each evaluation: a seeded sample
  stratified by speaker and by scripted/unscripted (--swivuriso-dev-per-speaker clips per speaker, about half
  unscripted where a speaker has them), references of at most --swivuriso-dev-max-tokens tokens so that none is cut
  off by --generation-max-length. Swivuriso dev speakers never train (separate split); their sentences are excluded.
- --select-on: which dev score picks the best checkpoint. auto (default) = as before (Soapies if given, else NCHLT);
  swivuriso+fleurs = 0.5 x Swivuriso dev CER + 0.5 x FLEURS dev CER ("combined_cer"); or one set's CER.
- --count-runaways: log, per dev set, how many outputs ran away (> 2.5x the reference and > 150 letters).
- --spec-augment: SpecAugment (masks random time stretches and frequency bands of the training audio's spectrogram;
  never at evaluation), with the --mask-* settings; the attention mask is passed so that masks fall on speech, not on
  the silence that pads every clip to 30 s.
"""
import argparse
import json
import math
import os
import random
import re
import sys
from dataclasses import dataclass

from math import gcd

import numpy as np
import soundfile as sf
import torch
from scipy.signal import resample_poly
from transformers import (Seq2SeqTrainer, Seq2SeqTrainingArguments, WhisperForConditionalGeneration,
                          WhisperProcessor)

sys.path.insert(0, os.path.dirname(__file__))
import fleurs  # noqa: E402
import soapies  # noqa: E402
import swivuriso  # noqa: E402
from nchlt import load_split  # noqa: E402
from scoring import normalise, score  # noqa: E402


def target_text(text):
    """What the model learns to write: the NCHLT transcript without non-speech tags like [s]."""
    return re.sub(r"\s+", " ", re.sub(r"\[[^\]]*\]", " ", text)).strip()


def read16k(path):
    audio, sr = sf.read(path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != 16000:  # NCHLT and FLEURS are 16 kHz; Soapies is 32 kHz
        g = gcd(sr, 16000)
        audio = resample_poly(audio, 16000 // g, sr // g).astype("float32")
    return audio


class Clips(torch.utils.data.Dataset):
    """A clip is one file ("path") or several joined with silence ("parts" + "gaps"). "lang" picks the language tag."""

    def __init__(self, clips, proc, language, attention_mask=False):
        self.clips, self.proc, self.attention_mask = clips, proc, attention_mask
        tok = proc.tokenizer
        self.prefix = {lang: tok.convert_tokens_to_ids(["<|startoftranscript|>", f"<|{lang}|>", "<|transcribe|>",
                                                        "<|notimestamps|>"])
                       for lang in {language, "en"}}
        self.language = language

    def __len__(self):
        return len(self.clips)

    def __getitem__(self, i):
        c = self.clips[i]
        if "parts" in c:
            pieces = []
            for k, p in enumerate(c["parts"]):
                if k:
                    pieces.append(np.zeros(int(16000 * c["gaps"][k - 1]), dtype="float32"))
                pieces.append(read16k(p))
            audio = np.concatenate(pieces)
        else:
            audio = read16k(c["path"])
        if self.attention_mask:  # which of the 3000 frames are audio, not padding (SpecAugment masks only those)
            f = self.proc.feature_extractor(audio, sampling_rate=16000, return_attention_mask=True)
            extra = {"attention_mask": f.attention_mask[0]}
        else:
            f, extra = self.proc.feature_extractor(audio, sampling_rate=16000), {}
        feats = f.input_features[0]
        tok = self.proc.tokenizer
        labels = (self.prefix[c.get("lang", self.language)] + tok(target_text(c["text"]), add_special_tokens=False).input_ids
                  + [tok.eos_token_id])
        return {"input_features": feats, "labels": labels, **extra}


def take_hours(clips, hours, seed):
    """A seeded random subset of clips adding up to about `hours` of audio."""
    pool = random.Random(seed).sample(clips, len(clips))
    out, total = [], 0.0
    for c in pool:
        if total >= hours * 3600:
            break
        out.append(c)
        total += c["duration"]
    return out


def stitch(xho, eng, n, seed, max_seconds):
    """n clips joining real isiXhosa and English clips: x+e, e+x or x+e+x, 0.1-0.4 s of silence between parts."""
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        pattern = rng.choice(["xe", "ex", "xex"])
        parts = [rng.choice(xho if p == "x" else eng) for p in pattern]
        gaps = [round(rng.uniform(0.1, 0.4), 2) for _ in parts[1:]]
        duration = sum(p["duration"] for p in parts) + sum(gaps)
        if duration > max_seconds:
            continue
        out.append({"id": f"stitch_{len(out):05d}", "speaker": "stitch", "parts": [p["path"] for p in parts],
                    "part_ids": [p["id"] for p in parts], "gaps": gaps, "duration": duration,
                    "text": " ".join(target_text(p["text"]) for p in parts), "pattern": pattern})
    return out


@dataclass
class Collator:
    proc: WhisperProcessor
    decoder_start_token_id: int

    def __call__(self, items):
        keys = ["input_features"] + (["attention_mask"] if "attention_mask" in items[0] else [])
        batch = self.proc.feature_extractor.pad([{k: x[k] for k in keys} for x in items], return_tensors="pt")
        labels = self.proc.tokenizer.pad([{"input_ids": x["labels"]} for x in items], return_tensors="pt")
        ids = labels["input_ids"].masked_fill(labels.attention_mask.ne(1), -100)  # padding is ignored by the loss
        if (ids[:, 0] == self.decoder_start_token_id).all():  # the model adds <|startoftranscript|> itself
            ids = ids[:, 1:]
        batch["labels"] = ids
        return batch


def split_dev(clips, n_speakers, seed):
    """Hold out n_speakers whole speakers (half women, half men), chosen with a fixed seed."""
    rng = random.Random(seed)
    by_gender = {}
    for spk, g in sorted({(c["speaker"], c["gender"]) for c in clips}):
        by_gender.setdefault(g, []).append(spk)
    dev = set()
    for g in sorted(by_gender):
        dev |= set(rng.sample(by_gender[g], n_speakers // 2))
    return [c for c in clips if c["speaker"] not in dev], [c for c in clips if c["speaker"] in dev], sorted(dev)


def swivuriso_dev_sample(clips, per_speaker, seed):
    """A fixed dev sample: per_speaker clips from every speaker, about half unscripted where the speaker has enough,
    the rest scripted (topped up from the other type when one runs short). Seeded; sorted by id."""
    rng = random.Random(seed)
    out = []
    for spk in sorted({c["speaker"] for c in clips}):
        mine = sorted((c for c in clips if c["speaker"] == spk), key=lambda c: c["id"])
        free = [c for c in mine if c["type"] == "unscripted"]
        read = [c for c in mine if c["type"] != "unscripted"]
        rng.shuffle(free)
        rng.shuffle(read)
        n_free = min(len(free), per_speaker // 2)
        n_read = min(len(read), per_speaker - n_free)
        n_free = min(len(free), per_speaker - n_read)
        out += free[:n_free] + read[:n_read]
    return sorted(out, key=lambda c: c["id"])


def steps_for(a, n_train):
    """--max-steps, or --epochs converted to optimiser steps and rounded up to a multiple of --eval-every."""
    if a.epochs is None:
        return a.max_steps
    steps = math.ceil(a.epochs * n_train / (a.batch_size * a.grad_accum))
    return max(a.eval_every, math.ceil(steps / a.eval_every) * a.eval_every)


def selection_metric(select_on, sets):
    """-> (metric_for_best_model, the dev sets averaged or None). `sets` = names of the dev sets scored."""
    if select_on == "auto":  # exactly the earlier rule
        return ("soapies_cer" if "soapies" in sets else "nchlt_cer" if "fleurs" in sets else "cer"), None
    if select_on == "swivuriso+fleurs":
        missing = {"swivuriso", "fleurs"} - set(sets)
        if missing:
            raise SystemExit(f"--select-on swivuriso+fleurs needs the {sorted(missing)} dev set(s)")
        return "combined_cer", ("swivuriso", "fleurs")
    if select_on not in sets:
        raise SystemExit(f"--select-on {select_on}: that dev set is not scored")
    return (f"{select_on}_cer" if len(sets) > 1 else "cer"), None


def apply_spec_augment(model, a):
    """SpecAugment on the training audio (transformers masks only in training mode, never at evaluation)."""
    model.config.apply_spec_augment = True
    for k in ("mask_time_prob", "mask_time_length", "mask_time_min_masks", "mask_feature_prob",
              "mask_feature_length", "mask_feature_min_masks"):
        setattr(model.config, k, getattr(a, k))


class CombinedTrainer(Seq2SeqTrainer):
    """Seq2SeqTrainer plus one more dev score, the mean of some dev sets' CER, added before the best checkpoint is
    chosen (so --select-on swivuriso+fleurs can use it) and written to the log."""

    def __init__(self, *args, combine=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.combine = combine

    def evaluate(self, eval_dataset=None, ignore_keys=None, metric_key_prefix="eval", **gen_kwargs):
        metrics = super().evaluate(eval_dataset, ignore_keys=ignore_keys, metric_key_prefix=metric_key_prefix,
                                   **gen_kwargs)
        if self.combine and metric_key_prefix == "eval" and eval_dataset is None:  # the call that scores every set
            value = round(sum(metrics[f"eval_{n}_cer"] for n in self.combine) / len(self.combine), 3)
            metrics["eval_combined_cer"] = value
            self.log({"eval_combined_cer": value})
        return metrics


def last_checkpoint(folder):
    """Newest checkpoint that finished writing (trainer_state.json is written last)."""
    if not os.path.isdir(folder):
        return None
    done = [d for d in os.listdir(folder) if d.startswith("checkpoint-")
            and os.path.exists(os.path.join(folder, d, "trainer_state.json"))]
    return os.path.join(folder, max(done, key=lambda d: int(d.split("-")[1]))) if done else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="openai/whisper-small")
    ap.add_argument("--language", default="sw")
    ap.add_argument("--max-steps", type=int, default=4000)
    ap.add_argument("--lr", type=float, default=1e-5)
    ap.add_argument("--warmup", type=int, default=500)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--grad-accum", type=int, default=2)
    ap.add_argument("--eval-every", type=int, default=500)
    ap.add_argument("--dev-speakers", type=int, default=6)
    ap.add_argument("--dev-clips", type=int, default=600, help="dev clips scored at each evaluation")
    ap.add_argument("--max-seconds", type=float, default=30.0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--fleurs-tsv", help="extra training data: a FLEURS split .tsv (added to train only, never to dev)")
    ap.add_argument("--fleurs-audio", help="folder holding that FLEURS split's .wav files")
    ap.add_argument("--generation-max-length", type=int, default=225)
    ap.add_argument("--fleurs-dev-tsv", help="also score FLEURS dev clips at each evaluation (information only;"
                    " the best checkpoint is still chosen on NCHLT dev, as in earlier runs)")
    ap.add_argument("--fleurs-dev-audio")
    ap.add_argument("--fleurs-dev-clips", type=int, default=200)
    ap.add_argument("--gradient-checkpointing", action="store_true",
                    help="recompute activations instead of storing them: less GPU memory, ~30%% slower")
    ap.add_argument("--only-existing", action="store_true",
                    help="use only clips whose audio is on disk (preflight with a few speakers downloaded)")
    ap.add_argument("--swivuriso-tsv", help="extra training data: Swivuriso train.tsv from src/swivuriso.py prepare")
    ap.add_argument("--swivuriso-audio", help="folder the Swivuriso TSV's file paths are relative to")
    ap.add_argument("--exclude-texts", nargs="*", help="files with one test sentence per line; Swivuriso training"
                    " clips with any of these sentences are dropped (leak filter)")
    ap.add_argument("--train-longest", type=int, default=0,
                    help="train only on the N clips with the longest transcripts (GPU memory check before a real run)")
    ap.add_argument("--english-xml", help="NCHLT English training XML (stage 4): English clips with the <|en|> tag")
    ap.add_argument("--english-hours", type=float, default=10.0, help="how much of NCHLT English to train on")
    ap.add_argument("--stitch", type=int, default=0, help="number of joined isiXhosa+English clips (needs --english-xml)")
    ap.add_argument("--soapies-root", help="folder with Soapies engxho (balanced_engxho.xml, ids/, extracted/): its dev"
                    " set is scored at each evaluation and picks the best checkpoint (never trained on, D-0016)")
    r = ap.add_argument_group("training recipe options (R-0035); the defaults are the earlier runs' behaviour")
    r.add_argument("--epochs", type=float, help="train this many passes over the training clips (overrides --max-steps)")
    r.add_argument("--lr-scheduler", default="linear", help="transformers scheduler name: linear | cosine | ...")
    r.add_argument("--save-total-limit", type=int, default=2)
    r.add_argument("--num-workers", type=int, default=4, help="data loader processes (0 on a small laptop)")
    r.add_argument("--swivuriso-dev-tsv", help="Swivuriso dev.tsv: scored at each evaluation (never trained on)")
    r.add_argument("--swivuriso-dev-audio")
    r.add_argument("--swivuriso-dev-per-speaker", type=int, default=22)
    r.add_argument("--swivuriso-dev-max-tokens", type=int, default=220,
                   help="only dev references this short, so --generation-max-length never cuts one off")
    r.add_argument("--select-on", default="auto",
                   choices=["auto", "nchlt", "fleurs", "swivuriso", "soapies", "swivuriso+fleurs"])
    r.add_argument("--count-runaways", action="store_true")
    r.add_argument("--spec-augment", action="store_true")
    r.add_argument("--mask-time-prob", type=float, default=0.05)
    r.add_argument("--mask-time-length", type=int, default=10)
    r.add_argument("--mask-time-min-masks", type=int, default=2)
    r.add_argument("--mask-feature-prob", type=float, default=0.10)
    r.add_argument("--mask-feature-length", type=int, default=8)
    r.add_argument("--mask-feature-min-masks", type=int, default=1)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    proc = WhisperProcessor.from_pretrained(a.model, language=a.language, task="transcribe")

    clips = [c for c in load_split(a.xml, a.root) if c["duration"] <= a.max_seconds and target_text(c["text"])]
    if a.only_existing:
        clips = [c for c in clips if os.path.exists(c["path"])]
    train, dev, dev_speakers = split_dev(clips, a.dev_speakers, a.seed)
    dev_texts = {normalise(c["text"]) for c in dev}  # every held-out dev sentence, before the 600-clip sample
    dev = random.Random(a.seed).sample(dev, min(a.dev_clips, len(dev)))
    extra, fleurs_dropped = [], 0
    if a.fleurs_tsv:  # added after the dev split, so dev (and test) stay identical to NCHLT-only runs
        fl = fleurs.load_split(a.fleurs_tsv, a.fleurs_audio)
        for c in fl:  # FLEURS keeps hyphens, digits and some punctuation; train on the exact form we score (D-0010)
            c["text"] = normalise(c["text"])
        extra = [c for c in fl if c["duration"] <= a.max_seconds and c["text"]]
        fleurs_dropped = len(fl) - len(extra)
        if a.only_existing:
            extra = [c for c in extra if os.path.exists(c["path"])]
        train = train + extra
    swiv, swiv_leaks, swiv_too_long_text = [], 0, 0
    if a.swivuriso_tsv:  # also added after the dev split (D-0024); text already normalised by swivuriso.prepare
        sw = [c for c in swivuriso.load_split(a.swivuriso_tsv, a.swivuriso_audio) if c["duration"] <= a.max_seconds]
        test_texts = set()
        for path in a.exclude_texts or []:
            with open(path, encoding="utf-8") as f:
                test_texts |= {normalise(line) for line in f if line.strip()}
        if not test_texts:  # fail closed: new data without a leak filter is never trained on
            sys.exit("--swivuriso-tsv needs --exclude-texts with the test and dev sentences")
        test_texts |= dev_texts  # the NCHLT dev speakers pick the checkpoint, so their sentences stay out too
        if a.swivuriso_dev_tsv:  # so do the Swivuriso dev sentences (the job's exclusion file has them already)
            test_texts |= {c["text"] for c in swivuriso.load_split(a.swivuriso_dev_tsv, a.swivuriso_dev_audio or "")}
        swiv = [c for c in sw if c["text"] not in test_texts]  # a test sentence never becomes training data
        swiv_leaks = len(sw) - len(swiv)
        n = len(swiv)  # Whisper writes at most 448 tokens (4 go to the prefix and end): longer transcripts can't be learned
        swiv = [c for c in swiv if len(proc.tokenizer(c["text"], add_special_tokens=False).input_ids) <= 440]
        swiv_too_long_text = n - len(swiv)
        assert not {c["text"] for c in swiv} & test_texts, "a test or dev sentence got into training"
        train = train + swiv
    english, stitched = [], []
    if a.english_xml:  # also added after the dev split; dev and test stay NCHLT isiXhosa
        eng = [c for c in load_split(a.english_xml, a.root) if c["duration"] <= a.max_seconds and target_text(c["text"])]
        if a.only_existing:
            eng = [c for c in eng if os.path.exists(c["path"])]
        english = [dict(c, lang="en") for c in take_hours(eng, a.english_hours, a.seed)]
        if a.stitch:
            xho = [c for c in train if c["speaker"] != "fleurs"]  # NCHLT isiXhosa training clips only
            stitched = stitch(xho, eng, a.stitch, a.seed, a.max_seconds)
            with open(os.path.join(a.out, "stitched.jsonl"), "w", encoding="utf-8") as f:
                for c in stitched:
                    f.write(json.dumps({k: c[k] for k in ("id", "part_ids", "gaps", "pattern", "text")},
                                       ensure_ascii=False) + "\n")
        train = train + english + stitched
    if a.train_longest:  # memory check: only the clips with the longest transcripts
        train = sorted(train, key=lambda c: len(target_text(c["text"])), reverse=True)[:a.train_longest]
    soapies_dev = []
    if a.soapies_root:
        R = a.soapies_root
        soapies_dev = soapies.load_split(os.path.join(R, "balanced_engxho.xml"),
                                         os.path.join(R, "ids", "cs_engxho_balanced", "transcriptions",
                                                      "engxho_dev_set_utterance_ids.txt"),
                                         os.path.join(R, "extracted"))
        for c in soapies_dev:  # score on the exact form we score test on
            c["text"] = normalise(c["text"])
        soapies_dev = [c for c in soapies_dev if c["path"] and c["text"]]
    fleurs_dev = []
    if a.fleurs_dev_tsv:
        fd = fleurs.load_split(a.fleurs_dev_tsv, a.fleurs_dev_audio)
        for c in fd:
            c["text"] = normalise(c["text"])
        fd = [c for c in fd if c["duration"] <= a.max_seconds and c["text"]]
        fleurs_dev = random.Random(a.seed).sample(fd, min(a.fleurs_dev_clips or len(fd), len(fd)))  # 0 = all
    swiv_dev = []
    if a.swivuriso_dev_tsv:
        sd = [c for c in swivuriso.load_split(a.swivuriso_dev_tsv, a.swivuriso_dev_audio or "")
              if c["duration"] <= a.max_seconds
              and len(proc.tokenizer(c["text"], add_special_tokens=False).input_ids) <= a.swivuriso_dev_max_tokens]
        swiv_dev = swivuriso_dev_sample(sd, a.swivuriso_dev_per_speaker, a.seed)
        assert not {c["speaker"] for c in swiv_dev} & {c["speaker"] for c in train}, "a dev speaker is in training"
    max_steps = steps_for(a, len(train))
    info = {"train_clips": len(train), "train_hours": round(sum(c["duration"] for c in train) / 3600, 2),
            "train_speakers": len({c["speaker"] for c in train}), "dev_speakers": dev_speakers,
            "dev_clips_scored": len(dev), "dropped_over_max_seconds": len(load_split(a.xml, a.root)) - len(clips),
            "fleurs_train_clips": len(extra), "fleurs_dropped_over_max_seconds": fleurs_dropped, "fleurs_train_hours": round(sum(c["duration"] for c in extra) / 3600, 2),
            "fleurs_dev_clips_scored": len(fleurs_dev),
            "swivuriso_train_clips": len(swiv), "swivuriso_train_hours": round(sum(c["duration"] for c in swiv) / 3600, 2),
            "swivuriso_dropped_test_sentences": swiv_leaks,
            "swivuriso_dropped_over_440_tokens": swiv_too_long_text, "swivuriso_train_speakers": len({c["speaker"] for c in swiv}),
            "english_train_clips": len(english), "english_train_hours": round(sum(c["duration"] for c in english) / 3600, 2),
            "stitched_clips": len(stitched), "stitched_hours": round(sum(c["duration"] for c in stitched) / 3600, 2),
            "soapies_dev_clips_scored": len(soapies_dev), "model": a.model, "batch_size": a.batch_size,
            "grad_accum": a.grad_accum, "gradient_checkpointing": a.gradient_checkpointing}
    if a.epochs is not None or swiv_dev or a.spec_augment or a.select_on != "auto" or a.lr_scheduler != "linear":
        info["recipe"] = {  # written only when a recipe option is used, so earlier runs' data_split.json stay the same
            "max_steps": max_steps, "epochs_requested": a.epochs,
            "epochs": round(max_steps * a.batch_size * a.grad_accum / len(train), 3), "lr_scheduler": a.lr_scheduler,
            "select_on": a.select_on, "swivuriso_dev_clips_scored": len(swiv_dev),
            "swivuriso_dev_speakers": len({c["speaker"] for c in swiv_dev}),
            "swivuriso_dev_unscripted": sum(c["type"] == "unscripted" for c in swiv_dev),
            "swivuriso_dev_hours": round(sum(c["duration"] for c in swiv_dev) / 3600, 2),
            "spec_augment": {k: getattr(a, k) for k in ("mask_time_prob", "mask_time_length", "mask_time_min_masks",
                                                        "mask_feature_prob", "mask_feature_length",
                                                        "mask_feature_min_masks")} if a.spec_augment else None,
            "generation_max_length": a.generation_max_length, "save_total_limit": a.save_total_limit}
    print(json.dumps(info), flush=True)
    with open(os.path.join(a.out, "data_split.json"), "w") as f:
        json.dump(info, f, indent=2)

    model = WhisperForConditionalGeneration.from_pretrained(a.model)
    model.generation_config.language = a.language
    model.generation_config.task = "transcribe"
    model.generation_config.forced_decoder_ids = None
    model.config.forced_decoder_ids = None
    if a.gradient_checkpointing:
        model.config.use_cache = False  # the decoder cache can't be used while recomputing activations
    if a.spec_augment:
        apply_spec_augment(model, a)

    def compute_metrics(pred):
        ids = pred.predictions
        ids[ids == -100] = proc.tokenizer.pad_token_id
        lab = pred.label_ids
        lab[lab == -100] = proc.tokenizer.pad_token_id
        hyps = proc.tokenizer.batch_decode(ids, skip_special_tokens=True)
        refs = proc.tokenizer.batch_decode(lab, skip_special_tokens=True)
        s = score(refs, hyps)
        out = {"wer": round(s["wer"], 2), "cer": round(s["cer"], 2)}
        if a.count_runaways:  # outputs that ran on (> 2.5x the reference and > 150 letters)
            out["runaways"] = sum(len(h) > 2.5 * len(r) and len(h) > 150
                                  for r, h in zip(map(normalise, refs), map(normalise, hyps)))
        return out

    evals = {"nchlt": Clips(dev, proc, a.language)}
    if fleurs_dev:
        evals["fleurs"] = Clips(fleurs_dev, proc, a.language)
    if soapies_dev:
        evals["soapies"] = Clips(soapies_dev, proc, a.language)
    if swiv_dev:
        evals["swivuriso"] = Clips(swiv_dev, proc, a.language)
    best, combine = selection_metric(a.select_on, list(evals))
    ckpts = os.path.join(a.out, "checkpoints")
    args = Seq2SeqTrainingArguments(
        output_dir=ckpts, per_device_train_batch_size=a.batch_size, gradient_accumulation_steps=a.grad_accum,
        per_device_eval_batch_size=32, learning_rate=a.lr, warmup_steps=a.warmup, max_steps=max_steps,
        lr_scheduler_type=a.lr_scheduler, bf16=torch.cuda.is_available(), eval_strategy="steps", eval_steps=a.eval_every,
        save_strategy="steps", save_steps=a.eval_every, save_total_limit=a.save_total_limit, load_best_model_at_end=True,
        metric_for_best_model=best, greater_is_better=False,
        gradient_checkpointing=a.gradient_checkpointing, predict_with_generate=True, generation_max_length=a.generation_max_length,
        logging_steps=25, report_to="none", dataloader_num_workers=a.num_workers, remove_unused_columns=False,
        label_names=["labels"], seed=a.seed)
    trainer_class, extra = (CombinedTrainer, {"combine": combine}) if combine else (Seq2SeqTrainer, {})
    trainer = trainer_class(model=model, args=args, train_dataset=Clips(train, proc, a.language, a.spec_augment),
                            eval_dataset=evals if len(evals) > 1 else evals["nchlt"],
                            data_collator=Collator(proc, model.config.decoder_start_token_id),
                            compute_metrics=compute_metrics, processing_class=proc.feature_extractor, **extra)
    resume = last_checkpoint(ckpts)
    print(f"resuming from {resume}" if resume else "starting from the stock model", flush=True)
    trainer.train(resume_from_checkpoint=resume)

    final = os.path.join(a.out, "final")
    trainer.save_model(final)
    proc.save_pretrained(final)
    with open(os.path.join(a.out, "log_history.json"), "w") as f:
        json.dump(trainer.state.log_history, f, indent=1)
    steps = trainer.state.global_step
    print(json.dumps({"best_checkpoint": trainer.state.best_model_checkpoint,
                      "best_dev_cer": trainer.state.best_metric, "steps": steps,
                      "peak_gpu_memory_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2) if torch.cuda.is_available() else None}),
          flush=True)


if __name__ == "__main__":
    main()
