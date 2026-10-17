"""Fine-tune Whisper on the NCHLT isiXhosa training split, optionally plus FLEURS (--fleurs-tsv/--fleurs-audio).

  python src/train.py --xml data/nchlt_xho/transcriptions/nchlt_xho.trn.xml --root data --out out/model \
      --model openai/whisper-small --language sw --max-steps 4000

- isiXhosa borrows Swahili's language tag (D-0007): every training target starts <|startoftranscript|><|sw|><|transcribe|>.
- A few training speakers are held out as a dev set to pick the best checkpoint; the 8 test speakers are never touched here.
- Checkpoints go to <out>/checkpoints/; if one exists the run resumes from it (survives a restarted machine).
- The best checkpoint (lowest dev CER) is saved to <out>/final with its processor, ready for src/baseline.py.
"""
import argparse
import json
import os
import random
import re
import sys
from dataclasses import dataclass

import numpy as np
import soundfile as sf
import torch
from transformers import (Seq2SeqTrainer, Seq2SeqTrainingArguments, WhisperForConditionalGeneration,
                          WhisperProcessor)

sys.path.insert(0, os.path.dirname(__file__))
import fleurs  # noqa: E402
from nchlt import load_split  # noqa: E402
from scoring import normalise, score  # noqa: E402


def target_text(text):
    """What the model learns to write: the NCHLT transcript without non-speech tags like [s]."""
    return re.sub(r"\s+", " ", re.sub(r"\[[^\]]*\]", " ", text)).strip()


class Clips(torch.utils.data.Dataset):
    def __init__(self, clips, proc):
        self.clips, self.proc = clips, proc

    def __len__(self):
        return len(self.clips)

    def __getitem__(self, i):
        c = self.clips[i]
        audio, sr = sf.read(c["path"], dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        assert sr == 16000, f"{c['path']}: {sr} Hz"  # NCHLT is 16 kHz; resampling would go here if not
        feats = self.proc.feature_extractor(audio, sampling_rate=16000).input_features[0]
        labels = self.proc.tokenizer(target_text(c["text"])).input_ids
        return {"input_features": feats, "labels": labels}


@dataclass
class Collator:
    proc: WhisperProcessor
    decoder_start_token_id: int

    def __call__(self, items):
        batch = self.proc.feature_extractor.pad([{"input_features": x["input_features"]} for x in items],
                                                return_tensors="pt")
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
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    clips = [c for c in load_split(a.xml, a.root) if c["duration"] <= a.max_seconds and target_text(c["text"])]
    if a.only_existing:
        clips = [c for c in clips if os.path.exists(c["path"])]
    train, dev, dev_speakers = split_dev(clips, a.dev_speakers, a.seed)
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
    fleurs_dev = []
    if a.fleurs_dev_tsv:
        fd = fleurs.load_split(a.fleurs_dev_tsv, a.fleurs_dev_audio)
        for c in fd:
            c["text"] = normalise(c["text"])
        fd = [c for c in fd if c["duration"] <= a.max_seconds and c["text"]]
        fleurs_dev = random.Random(a.seed).sample(fd, min(a.fleurs_dev_clips, len(fd)))
    info = {"train_clips": len(train), "train_hours": round(sum(c["duration"] for c in train) / 3600, 2),
            "train_speakers": len({c["speaker"] for c in train}), "dev_speakers": dev_speakers,
            "dev_clips_scored": len(dev), "dropped_over_max_seconds": len(load_split(a.xml, a.root)) - len(clips),
            "fleurs_train_clips": len(extra), "fleurs_dropped_over_max_seconds": fleurs_dropped, "fleurs_train_hours": round(sum(c["duration"] for c in extra) / 3600, 2),
            "fleurs_dev_clips_scored": len(fleurs_dev), "model": a.model, "batch_size": a.batch_size,
            "grad_accum": a.grad_accum, "gradient_checkpointing": a.gradient_checkpointing}
    print(json.dumps(info), flush=True)
    with open(os.path.join(a.out, "data_split.json"), "w") as f:
        json.dump(info, f, indent=2)

    proc = WhisperProcessor.from_pretrained(a.model, language=a.language, task="transcribe")
    model = WhisperForConditionalGeneration.from_pretrained(a.model)
    model.generation_config.language = a.language
    model.generation_config.task = "transcribe"
    model.generation_config.forced_decoder_ids = None
    model.config.forced_decoder_ids = None
    if a.gradient_checkpointing:
        model.config.use_cache = False  # the decoder cache can't be used while recomputing activations

    def compute_metrics(pred):
        ids = pred.predictions
        ids[ids == -100] = proc.tokenizer.pad_token_id
        lab = pred.label_ids
        lab[lab == -100] = proc.tokenizer.pad_token_id
        hyps = proc.tokenizer.batch_decode(ids, skip_special_tokens=True)
        refs = proc.tokenizer.batch_decode(lab, skip_special_tokens=True)
        s = score(refs, hyps)
        return {"wer": round(s["wer"], 2), "cer": round(s["cer"], 2)}

    ckpts = os.path.join(a.out, "checkpoints")
    args = Seq2SeqTrainingArguments(
        output_dir=ckpts, per_device_train_batch_size=a.batch_size, gradient_accumulation_steps=a.grad_accum,
        per_device_eval_batch_size=32, learning_rate=a.lr, warmup_steps=a.warmup, max_steps=a.max_steps,
        lr_scheduler_type="linear", bf16=torch.cuda.is_available(), eval_strategy="steps", eval_steps=a.eval_every,
        save_strategy="steps", save_steps=a.eval_every, save_total_limit=2, load_best_model_at_end=True,
        metric_for_best_model="nchlt_cer" if fleurs_dev else "cer", greater_is_better=False,
        gradient_checkpointing=a.gradient_checkpointing, predict_with_generate=True, generation_max_length=a.generation_max_length,
        logging_steps=25, report_to="none", dataloader_num_workers=4, remove_unused_columns=False,
        label_names=["labels"], seed=a.seed)
    trainer = Seq2SeqTrainer(model=model, args=args, train_dataset=Clips(train, proc), eval_dataset={"nchlt": Clips(dev, proc), "fleurs": Clips(fleurs_dev, proc)} if fleurs_dev else Clips(dev, proc),
                             data_collator=Collator(proc, model.config.decoder_start_token_id),
                             compute_metrics=compute_metrics, processing_class=proc.feature_extractor)
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
