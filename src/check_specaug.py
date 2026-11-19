"""Check SpecAugment the way src/train.py runs it (R-0035 preflight; Neon's pre-flight memo, Q4):
1. the Collator's batch carries an attention mask of shape (batch, 3000) that marks each clip's own audio frames;
2. the attention mask reaches the model's forward call;
3. in training mode, time masks fall only on audio frames (never on the 30 s padding), and frequency masks appear;
4. in evaluation mode nothing is masked (the encoder sees the features unchanged).

  python src/check_specaug.py --model openai/whisper-medium --swivuriso-tsv data/swivuriso_16k/dev.tsv \
      --swivuriso-audio data/swivuriso_16k [--mask-* as in train.py]
Exits non-zero with the reason if any check fails. Uses train.py's own Clips, Collator and apply_spec_augment.
"""
import argparse
import os
import random
import sys

import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor

sys.path.insert(0, os.path.dirname(__file__))
import swivuriso  # noqa: E402
import train  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="openai/whisper-tiny")
    ap.add_argument("--swivuriso-tsv", required=True)
    ap.add_argument("--swivuriso-audio", required=True)
    ap.add_argument("--clips", type=int, default=8)
    ap.add_argument("--trials", type=int, default=20, help="training-mode forward passes (masks are random)")
    for k, v in (("mask-time-prob", 0.05), ("mask-feature-prob", 0.10)):
        ap.add_argument("--" + k, type=float, default=v)
    for k, v in (("mask-time-length", 10), ("mask-time-min-masks", 2), ("mask-feature-length", 8),
                 ("mask-feature-min-masks", 1)):
        ap.add_argument("--" + k, type=int, default=v)
    a = ap.parse_args()

    proc = WhisperProcessor.from_pretrained(a.model, language="sw", task="transcribe")
    clips = [c for c in swivuriso.load_split(a.swivuriso_tsv, a.swivuriso_audio) if c["duration"] <= 30]
    clips = sorted(random.Random(1).sample(clips, min(a.clips, len(clips))), key=lambda c: c["duration"])
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = WhisperForConditionalGeneration.from_pretrained(a.model).to(device)
    train.apply_spec_augment(model, a)
    data = train.Clips(clips, proc, "sw", attention_mask=True)
    batch = train.Collator(proc, model.config.decoder_start_token_id)([data[i] for i in range(len(clips))])
    batch = {k: v.to(device) for k, v in batch.items()}

    am = batch["attention_mask"]
    frames = am.sum(-1)
    expected = torch.tensor([min(3000, int(round(c["duration"] * 100))) for c in clips], device=device)
    assert am.shape == (len(clips), 3000), f"attention mask shape {tuple(am.shape)}"
    assert (frames - expected).abs().max() <= 2, f"attention mask lengths {frames.tolist()} vs audio {expected.tolist()}"
    print(f"1. attention mask OK: shape {tuple(am.shape)}, audio frames {frames.tolist()}")

    seen = {}

    def capture(module, args, kwargs):
        seen["features"] = (kwargs.get("input_features") if "input_features" in kwargs else args[0]).detach().clone()

    def capture_mask(module, args, kwargs):
        seen["attention_mask"] = kwargs.get("attention_mask")

    model.model.encoder.register_forward_pre_hook(capture, with_kwargs=True)
    model.model.register_forward_pre_hook(capture_mask, with_kwargs=True)

    time_hits = feat_hits = 0
    for t in range(a.trials):
        model.train()
        feats = batch["input_features"].clone()  # transformers masks in place
        with torch.no_grad():
            model(input_features=feats, attention_mask=batch["attention_mask"], labels=batch["labels"])
        assert seen["attention_mask"] is not None and torch.equal(seen["attention_mask"], batch["attention_mask"]), \
            "the attention mask did not reach the model's forward call"
        got, orig = seen["features"], batch["input_features"]
        zeroed = (got == 0) & (orig != 0)
        time_cols = zeroed.all(dim=1)  # (batch, 3000): whole frame (all 80 bands) zeroed = a time mask
        for i in range(len(clips)):
            cols = time_cols[i].nonzero().flatten()
            if len(cols):
                assert cols.max() < frames[i], f"clip {i}: a time mask at frame {cols.max().item()}, beyond its audio"
                time_hits += 1
        feat_rows = zeroed.all(dim=2)  # (batch, 80): whole band zeroed = a frequency mask
        feat_hits += int(feat_rows.any(dim=1).sum())
    assert time_hits > 0, "no time mask in training mode"
    assert a.mask_feature_prob == 0 or feat_hits > 0, "no frequency mask in training mode"
    print(f"2. attention mask reaches the model's forward call")
    print(f"3. training mode: time masks in {time_hits} of {a.trials * len(clips)} clip-passes, all inside the audio; "
          f"frequency masks in {feat_hits}")

    model.eval()
    with torch.no_grad():
        model(input_features=batch["input_features"].clone(), attention_mask=batch["attention_mask"],
              labels=batch["labels"])
    assert torch.equal(seen["features"], batch["input_features"]), "features were masked in evaluation mode"
    print("4. evaluation mode: no masking")
    print(f"SpecAugment check OK on {device}", {k: getattr(model.config, k) for k in (
        "apply_spec_augment", "mask_time_prob", "mask_time_length", "mask_time_min_masks", "mask_feature_prob",
        "mask_feature_length", "mask_feature_min_masks")})


if __name__ == "__main__":
    main()
