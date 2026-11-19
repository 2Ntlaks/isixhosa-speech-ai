"""Score a Whisper model (stock or fine-tuned) on a test set: NCHLT (--xml), FLEURS (--fleurs-tsv + --fleurs-audio),
Swivuriso (--swivuriso-tsv + --swivuriso-audio, prepared by src/swivuriso.py) or Soapies (--soapies-root).
Greedy decoding with transformers, batched, no reliability rules: the decoding behind every score up to R-0032.
src/eval_guarded.py scores the same clips with Whisper's reliability rules (R-0033).

  python src/baseline.py --xml data/nchlt_xho/transcriptions/nchlt_xho.tst.xml --root data --out out \
      --model openai/whisper-small --language auto
  python src/baseline.py --fleurs-tsv data/fleurs_xh_za/test.tsv --fleurs-audio data/fleurs_xh_za/audio/test \
      --root data --out out --model models/R-0004 --language sw

--language auto lets Whisper pick a language per clip (it has no isiXhosa tag) and records which one it picked.
--dry-run skips the model and uses the reference text as the "guess" (should score 0 %), to test the plumbing.
Writes to --out: predictions.jsonl, metrics.json, samples.md.
"""
import argparse
import json
import os
import platform
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import testsets  # noqa: E402  (test-set loading and reporting shared with eval_guarded.py and eval_omni.py)


def whisper_transcriber(model_name, language, max_new_tokens):
    import numpy as np
    import soundfile as sf
    import torch
    import torchaudio
    from transformers import WhisperForConditionalGeneration, WhisperProcessor

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    proc = WhisperProcessor.from_pretrained(model_name)
    model = WhisperForConditionalGeneration.from_pretrained(model_name, torch_dtype=dtype).to(device).eval()

    def load(path):
        audio, sr = sf.read(path, dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if sr != 16000:
            audio = torchaudio.functional.resample(torch.from_numpy(audio), sr, 16000).numpy()
        return np.ascontiguousarray(audio)

    def transcribe(clips):
        feats = proc([load(c["path"]) for c in clips], sampling_rate=16000, return_tensors="pt").input_features
        feats = feats.to(device, dtype)
        with torch.no_grad():
            if language == "auto":
                ids = model.detect_language(input_features=feats)
                langs = [t.strip("<|>") for t in proc.tokenizer.convert_ids_to_tokens(ids.tolist())]
            else:
                langs = [language] * len(clips)
            out = model.generate(feats, language=langs, task="transcribe", max_new_tokens=max_new_tokens)
        return proc.batch_decode(out, skip_special_tokens=True), langs

    env = {"torch": torch.__version__, "device": device,
           "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None}
    return transcribe, env


def main():
    ap = argparse.ArgumentParser()
    testsets.add_args(ap)  # --xml/--fleurs-tsv/--swivuriso-tsv/--soapies-root, --root, --train-*, --max-seconds, ...
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="openai/whisper-small")
    ap.add_argument("--language", default="auto")
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-new-tokens", type=int, default=225, help="FLEURS sentences need up to ~145 tokens")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    kind, clips, too_long = testsets.load(a)

    if a.dry_run:
        transcribe, env = (lambda b: ([c["text"] for c in b], ["dry"] * len(b))), {"device": "none"}
    else:
        transcribe, env = whisper_transcriber(a.model, a.language, a.max_new_tokens)

    order = sorted(range(len(clips)), key=lambda i: clips[i]["duration"])  # similar lengths batch well
    t0 = time.time()
    for k in range(0, len(order), a.batch_size):
        batch = [clips[i] for i in order[k: k + a.batch_size]]
        hyps, langs = transcribe(batch)
        for c, h, l in zip(batch, hyps, langs):
            c["hyp"], c["lang"] = h.strip(), l
        if (k // a.batch_size) % 10 == 0:
            print(f"  {k + len(batch)}/{len(clips)} clips, {time.time() - t0:.0f} s", flush=True)
    secs = time.time() - t0

    if not a.dry_run:
        import transformers
        env["transformers"] = transformers.__version__
    metrics = testsets.report(a, kind, clips, too_long, model=a.model, language=a.language,
                              max_new_tokens=a.max_new_tokens, seconds=secs, extra={"batch_size": a.batch_size},
                              env={**env, "python": platform.python_version()})
    print(json.dumps({k: metrics[k] for k in ("wer", "cer", "exact_match_pct", "detected_languages", "seconds")}))


if __name__ == "__main__":
    main()
